/* globals Quasar, Vue, _, windowMixin, LNbits, LOCALE */

window.app = Vue.createApp({
  el: '#vue',
  mixins: [window.windowMixin],
  data() {
    return {
      userLocale: navigator.language || 'en-GB',
      allowances: [],
      healthWarning: '',
      healthTimer: null,
      historyDialog: {show: false, rows: [], loading: false},
      historyColumns: [
        {name: 'scheduled', label: 'Scheduled', field: row => this.formatDatetime(new Date(row.scheduled_at * 1000).toISOString()), align: 'left'},
        {name: 'completed', label: 'Completed', field: row => this.formatDatetime(new Date(row.completed_at * 1000).toISOString()), align: 'left'},
        {name: 'outcome', label: 'Outcome', field: 'outcome', align: 'left'}
      ],
      currencies: [],
      fiatRates: {},
      allowanceTable: {
        columns: [
          {name: 'name', align: 'left', label: 'Description', field: 'name', sortable: true},
          {name: 'amount', align: 'right', label: 'Amount', field: 'amount', sortable: true, sort: (a, b) => {
            const numA = parseFloat(a);
            const numB = parseFloat(b);
            if (isNaN(numA) && isNaN(numB)) return 0;
            if (isNaN(numA)) return 1;
            if (isNaN(numB)) return -1;
            return numA - numB;
          }},
          {name: 'lightning_address', align: 'left', label: 'Recipient', field: 'lightning_address', sortable: true},
          {name: 'frequency_type', align: 'left', label: 'Frequency', field: 'frequency_type', sortable: true, sort: (a, b) => {
            const order = ['once', 'minutely', 'hourly', 'daily', 'weekly', 'monthly', 'yearly']
            return order.indexOf(a) - order.indexOf(b)
          }},
          {name: 'next_payment_date', align: 'left', label: 'Next Payment', field: 'next_payment_date', sortable: true,
            sort: (a, b) => (Date.parse(a) || 0) - (Date.parse(b) || 0)},
          {name: 'last_success_time', align: 'left', label: 'Last Success', field: 'last_success_time', sortable: true},
          {name: 'status', align: 'center', label: 'Status', field: 'active', sortable: true, sort: (a, b, rowA, rowB) => {
            const getStatusValue = (row) => {
              if (row.last_error) return 2
              if (row.active) return 1
              return 0
            }
            return getStatusValue(rowA) - getStatusValue(rowB)
          }}
        ],
        pagination: {
          rowsPerPage: 10
        },
        filter: '',
        loading: false
      },
      formDialog: {
        show: false,
        loading: false,
        data: {}
      },
      frequencyOptions: [
        {label: 'Once', value: 'once'},
        {label: 'Minutely', value: 'minutely'},
        {label: 'Hourly', value: 'hourly'},
        {label: 'Daily', value: 'daily'},
        {label: 'Weekly', value: 'weekly'},
        {label: 'Monthly', value: 'monthly'},
        {label: 'Yearly', value: 'yearly'}
      ]
    }
  },
  methods: {
    async loadHealth() {
      if (!this.g?.user?.wallets?.length) return
      try {
        const responses = await Promise.all(this.g.user.wallets.map(wallet =>
          LNbits.api.request('GET', '/allowance/api/v1/health', wallet.inkey)))
        const checks = responses.map(response => response.data)
        if (checks.some(check => !check.scheduler_ok)) {
          this.healthWarning = 'The allowance scheduler is not healthy. Contact the server operator.'
        } else {
          const overdue = checks.reduce((sum, check) => sum + check.overdue, 0)
          const pending = checks.reduce((sum, check) => sum + check.pending, 0)
          this.healthWarning = overdue || pending ? `${overdue} overdue allowances; ${pending} unresolved payments. Check their status.` : ''
        }
      } catch (_) {
        this.healthWarning = 'Allowance status is unavailable. The extension may be disabled or unreachable.'
      }
    },
    async showHistory(row) {
      const wallet = this.g.user.wallets.find(wallet => wallet.id === row.wallet)
      if (!wallet) return
      this.historyDialog = {show: true, rows: [], loading: true}
      try {
        const response = await LNbits.api.request('GET', `/allowance/api/v1/allowance/${row.id}/history`, wallet.inkey)
        this.historyDialog.rows = response.data
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      } finally {
        this.historyDialog.loading = false
      }
    },
    getAllowances() {
      this.loadHealth()

      this.allowanceTable.loading = true
      
      const wallet = this.g.user.wallets[0]
      if (!wallet) {

        this.allowanceTable.loading = false
        return
      }
      
      LNbits.api
        .request(
          'GET',
          '/allowance/api/v1/allowance',
          wallet.adminkey
        )
        .then(response => {

          this.allowances = response.data
        })
        .catch(err => {

          LNbits.utils.notifyApiError(err)
        })
        .finally(() => {
          this.allowanceTable.loading = false
        })
    },
    closeFormDialog() {
      this.formDialog.show = false
      this.formDialog.data = {}
    },
    openCreateDialog() {
      // For Quasar QDate/QTime, we need "YYYY-MM-DD HH:mm" format in LOCAL time
      // Default to 5 minutes in the future to ensure first payment is made
      const fiveMinutesFromNow = new Date(Date.now() + 5 * 60 * 1000)
      const defaultStart = this.toQuasarDatetimeString(fiveMinutesFromNow)
      this.formDialog.data = {
        memo: '',
        wallet: this.g.user.wallets[0].id,
        currency: 'sats',
        frequency_type: 'weekly',
        timezone_name: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
        active: true,
        start_datetime: defaultStart
      }
      this.formDialog.show = true

    },
    saveAllowance(event) {
      if (event) {
        event.preventDefault()
      }

      if (!this.formDialog.show) {

        return
      }
      
      const errors = []
      if (!this.formDialog.data.name) errors.push('Description is required')
      if (!this.formDialog.data.wallet) errors.push('Wallet is required')
      if (!this.formDialog.data.lightning_address) errors.push('Lightning address is required')
      if (!this.formDialog.data.amount || this.formDialog.data.amount <= 0) errors.push('Amount must be greater than 0')
      if (!this.formDialog.data.frequency_type) errors.push('Frequency is required')
      if (!this.formDialog.data.start_datetime) errors.push('Start date & time is required')

      if (!this.formDialog.data.id && this.formDialog.data.start_datetime) {
        const startDate = new Date(this.formDialog.data.start_datetime.replace(' ', 'T'))
        const now = new Date()
        const oneMinuteFromNow = new Date(now.getTime() + 60 * 1000)
        if (startDate < oneMinuteFromNow) {
          errors.push('Start date & time must be at least 1 minute in the future.')
        }
      }

      if (this.formDialog.data.end_datetime && this.formDialog.data.start_datetime) {
        const startDate = new Date(this.formDialog.data.start_datetime.replace(' ', 'T'))
        const endDate = new Date(this.formDialog.data.end_datetime.replace(' ', 'T'))
        if (endDate <= startDate) {
          errors.push('End date must be after start date')
        }
      }

      if (this.formDialog.data.active && this.formDialog.data.end_datetime) {
        const endDate = new Date(this.formDialog.data.end_datetime.replace(' ', 'T'))
        const now = new Date()
        if (endDate < now) {
          errors.push('Cannot activate allowance: end date is in the past')
        }
      }

      if (errors.length > 0) {

        this.$q.notify({
          type: 'negative',
          message: 'Validation failed: ' + errors.join(', '),
          timeout: 5000,
          position: 'top'
        })
        return
      }

      const wallet = _.findWhere(this.g.user.wallets, {
        id: this.formDialog.data.wallet
      })

      if (!wallet) {

        LNbits.utils.notifyApiError('No wallet selected')
        return
      }

      const data = _.clone(this.formDialog.data)
      

      // Don't convert currency amounts here - conversion happens at payment time
      let amount = parseFloat(data.amount) || 0

      if (!data.currency || data.currency === 'sats' || data.currency === 'satoshis') {
        amount = Math.round(amount)
      }

      const backendData = {
        id: data.id,
        revision: data.revision,
        name: data.name,  // Keep name field as expected by backend
        memo: data.memo ?? '',
        wallet: data.wallet,
        lightning_address: data.lightning_address,
        amount: amount,  // Store the original amount (0.02 for GBP, 10 for sats)
        currency: data.currency || 'sats',
        active: Boolean(data.active),  // Ensure boolean type
        end_datetime: data.end_datetime ? new Date(data.end_datetime.replace(' ', 'T')).toISOString() : null
      }

      // Only include start_datetime and frequency_type when creating (not updating)
      // These fields are locked after creation
      if (!data.id) {
        backendData.frequency_type = data.frequency_type
        backendData.timezone_name = data.timezone_name
        backendData.start_datetime = data.start_datetime ? new Date(data.start_datetime.replace(' ', 'T')).toISOString() : new Date().toISOString()
      }

      if (backendData.id) {

        this.updateAllowance(wallet, backendData)
      } else {

        this.createAllowance(wallet, backendData)
      }
    },
    createAllowance(wallet, data) {

      this.formDialog.loading = true

      LNbits.api
        .request('POST', '/allowance/api/v1/allowance', wallet.adminkey, data)
        .then(response => {
          this.getAllowances()
          this.formDialog.show = false
          this.resetFormData()
          this.$q.notify({
            type: 'positive',
            message: 'Allowance created successfully'
          })
        })
        .catch(err => {
          LNbits.utils.notifyApiError(err)
        })
        .finally(() => {
          this.formDialog.loading = false
        })
    },
    updateAllowance(wallet, data) {
      this.formDialog.loading = true
      LNbits.api
        .request('PUT', '/allowance/api/v1/allowance/' + data.id, wallet.adminkey, data)
        .then(response => {
          this.getAllowances()
          this.formDialog.show = false
          this.resetFormData()
          this.$q.notify({
            type: 'positive',
            message: 'Allowance updated successfully'
          })
        })
        .catch(err => {
          LNbits.utils.notifyApiError(err)
        })
        .finally(() => {
          this.formDialog.loading = false
        })
    },
    resetFormData() {
      this.formDialog = {
        show: false,
        loading: false,
        data: {}
      }
    },
    reconcileAllowance(row) {
      const wallet = this.g.user.wallets.find(wallet => wallet.id === row.wallet)
      if (!wallet) return
      LNbits.api.request('POST', `/allowance/api/v1/allowance/${row.id}/reconcile`, wallet.adminkey)
        .then(response => {
          Quasar.Notify.create({type: response.data.pending ? 'warning' : response.data.success === false ? 'negative' : 'positive', message: response.data.message})
          this.getAllowances()
        })
        .catch(LNbits.utils.notifyApiError)
    },
    openUpdateDialog(row) {

      this.formDialog.data = {}

      const clonedData = JSON.parse(JSON.stringify(row))

      this.formDialog.data = {
        id: clonedData.id,
        revision: clonedData.revision,
        name: clonedData.name,
        wallet: clonedData.wallet,
        lightning_address: clonedData.lightning_address,
        amount: clonedData.amount,  // Amount is already in the correct format (0.02 for GBP, 10 for sats)
        currency: clonedData.currency,
        frequency_type: clonedData.frequency_type,
        start_datetime: clonedData.start_datetime, // Add missing start_datetime
        next_payment_date: clonedData.next_payment_date,
        memo: clonedData.memo ?? '',
        timezone_name: clonedData.timezone_name || 'UTC',
        end_datetime: clonedData.end_datetime
      }

      // Convert datetime fields from UTC (API) to local time (for Quasar)
      // Quasar QDate/QTime needs "YYYY-MM-DD HH:mm" format in local time
      if (this.formDialog.data.start_datetime) {
        if (typeof this.formDialog.data.start_datetime === 'string') {
          const utcDate = new Date(this.formDialog.data.start_datetime.replace(' ', 'T'))
          this.formDialog.data.start_datetime = this.toQuasarDatetimeString(utcDate)

        }
      }

      if (this.formDialog.data.end_datetime) {
        if (typeof this.formDialog.data.end_datetime === 'string') {
          const utcDate = new Date(this.formDialog.data.end_datetime.replace(' ', 'T'))
          this.formDialog.data.end_datetime = this.toQuasarDatetimeString(utcDate)

        }
      }
      
      const originalActive = row.active

      let activeValue = false  // Default to false if not set

      if (originalActive !== null && originalActive !== undefined) {
        if (typeof originalActive === 'boolean') {
          activeValue = originalActive
        } else if (typeof originalActive === 'number') {
          activeValue = originalActive !== 0
        } else if (typeof originalActive === 'string') {
          activeValue = originalActive.toLowerCase() === 'true' || originalActive === '1'
        } else {
          activeValue = Boolean(originalActive)
        }
      }
      
      this.$set ? this.$set(this.formDialog.data, 'active', activeValue) : (this.formDialog.data.active = activeValue)

      this.formDialog.show = true
      
      this.$nextTick(() => {

        this.$forceUpdate()
      })
    },
    deleteAllowance(id) {
      const allowance = _.findWhere(this.allowances, {id: id})
      if (!allowance) return
      
      LNbits.utils
        .confirmDialog('Are you sure you want to delete this allowance?')
        .onOk(() => {
          const wallet = _.findWhere(this.g.user.wallets, {id: allowance.wallet})
          if (!wallet) return
          
          LNbits.api
            .request(
              'DELETE',
              '/allowance/api/v1/allowance/' + id,
              wallet.adminkey
            )
            .then(() => {
              this.allowances = _.reject(this.allowances, obj => obj.id == id)
              this.$q.notify({
                type: 'positive',
                message: 'Allowance deleted successfully!'
              })
            })
            .catch(err => {
              LNbits.utils.notifyApiError(err)
            })
        })
    },
    exportCSV() {
      LNbits.utils.exportCSV(this.allowanceTable.columns, this.allowances, 'allowances')
    },
    copyText(text) {
      navigator.clipboard.writeText(text)
      this.$q.notify({message: 'Copied to clipboard', type: 'positive'})
    },
    updateFiatRate(currency) {
      if (currency && currency !== 'sats' && currency !== 'satoshis') {
        LNbits.api
          .request('GET', '/api/v1/rate/' + currency, null)
          .then(response => {
            let rates = _.clone(this.fiatRates)
            rates[currency] = response.data.rate
            this.fiatRates = rates

          })
          .catch(err => {

          })
      }
    },
    toggleActive() {

      this.formDialog.data.active = !this.formDialog.data.active

      this.$forceUpdate()
    },
    formatErrorTime(timestamp) {
      if (!timestamp) return ''

      let date

      if (typeof timestamp === 'string') {
        date = new Date(timestamp)

        if (isNaN(date.getTime())) {
          const ts = parseInt(timestamp)
          if (!isNaN(ts) && ts > 0) {
            date = new Date(ts * 1000)
          }
        }
      } else if (typeof timestamp === 'number') {
        date = new Date(timestamp * 1000)
      } else {
        return 'Invalid datetime'
      }

      if (!date || isNaN(date.getTime())) return 'Invalid datetime'

      const now = new Date()
      const diff = now - date

      const minutes = Math.floor(diff / 60000)
      const hours = Math.floor(diff / 3600000)
      const days = Math.floor(diff / 86400000)

      if (minutes < 1) return 'Just now'
      if (minutes < 60) return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`
      if (hours < 24) return `${hours} hour${hours !== 1 ? 's' : ''} ago`
      if (days < 7) return `${days} day${days !== 1 ? 's' : ''} ago`

      return date.toLocaleString(this.userLocale, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    },
    toLocalDatetimeString(date) {
      // Convert a Date object to YYYY-MM-DDTHH:MM format in local timezone
      // toISOString() gives UTC, but we can offset to local time first
      const offset = date.getTimezoneOffset() * 60000 // offset in milliseconds
      const localDate = new Date(date.getTime() - offset)
      return localDate.toISOString().slice(0, 16) // "YYYY-MM-DDTHH:mm"
    },
    toQuasarDatetimeString(date) {
      const offset = date.getTimezoneOffset() * 60000 // offset in milliseconds
      const localDate = new Date(date.getTime() - offset)
      const isoString = localDate.toISOString() // "YYYY-MM-DDTHH:mm:ss.sssZ"
      return isoString.slice(0, 16).replace('T', ' ')
    },
    formatDatetime(timestamp) {
      if (!timestamp) return ''

      const date = new Date(timestamp)
      if (!date || isNaN(date.getTime())) return 'Invalid datetime'

      return date.toLocaleString(this.userLocale, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    },
    formatDatetimeForDisplay(datetimeString) {
      if (!datetimeString) return ''

      const date = new Date(datetimeString.replace(' ', 'T'))
      if (!date || isNaN(date.getTime())) return ''

      return date.toLocaleString(this.userLocale, {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      })
    },
    calculateNextPaymentDate(startDate, frequencyType) {
      const date = new Date(startDate.replace(' ', 'T'))

      switch (frequencyType) {
        case 'minutely':
          date.setMinutes(date.getMinutes() + 1)
          break
        case 'hourly':
          date.setHours(date.getHours() + 1)
          break
        case 'weekly':
          date.setDate(date.getDate() + 7)
          break
        case 'monthly':
          date.setMonth(date.getMonth() + 1)
          break
        case 'yearly':
          date.setFullYear(date.getFullYear() + 1)
          break
        default:
          date.setDate(date.getDate() + 7) // Default to weekly
      }

      return date.toISOString()
    },
    loadCurrencies() {

      LNbits.api
        .request('GET', '/api/v1/currencies')
        .then(response => {

          this.currencies = ['sats', ...response.data]
        })
        .catch(err => {

          if (this.g?.user?.wallets?.[0]?.inkey) {
            LNbits.api
              .request('GET', '/api/v1/currencies', this.g.user.wallets[0].inkey)
              .then(response => {

                this.currencies = ['sats', ...response.data]
              })
              .catch(authErr => {

                this.currencies = ['sats', 'USD', 'EUR']
              })
          } else {

            this.currencies = ['sats', 'USD', 'EUR']
          }
        })
    },
    isDateInFuture(date) {
      // date format: "YYYY/MM/DD" (QDate format)
      const selectedDate = new Date(date)
      const today = new Date()
      today.setHours(0, 0, 0, 0) // Reset to start of day
      selectedDate.setHours(0, 0, 0, 0)
      return selectedDate >= today
    },
    getTodayDateString() {
      const today = new Date()
      const year = today.getFullYear()
      const month = String(today.getMonth() + 1).padStart(2, '0')
      const day = String(today.getDate()).padStart(2, '0')
      return `${year}/${month}/${day}`
    }
  },
  computed: {
    isEndDateInPast() {
      if (!this.formDialog.data.end_datetime || this.formDialog.data.end_datetime === '') {
        return false
      }
      const endDate = new Date(this.formDialog.data.end_datetime.replace(' ', 'T'))
      const now = new Date()
      return endDate < now
    },
    formattedStartDatetime() {
      if (!this.formDialog.data.start_datetime || this.formDialog.data.start_datetime === '') return ''
      return this.formatDatetimeForDisplay(this.formDialog.data.start_datetime)
    },
    formattedEndDatetime() {
      if (!this.formDialog.data.end_datetime || this.formDialog.data.end_datetime === '') return ''
      return this.formatDatetimeForDisplay(this.formDialog.data.end_datetime)
    }
  },
  watch: {
    'formDialog.data.currency': function(newVal) {
      if (newVal) {
        this.updateFiatRate(newVal)
      }
    },
    'formDialog.data.end_datetime': function(newVal) {
      if (newVal && newVal.trim() !== '') {
        const endDate = new Date(newVal.replace(' ', 'T'))
        const now = new Date()
        if (endDate < now) {

          this.formDialog.data.active = false
        }
      }
    }
  },
  beforeUnmount() {
    clearInterval(this.healthTimer)
  },
  created() {
    this.healthTimer = setInterval(() => this.loadHealth(), 60000)
    if (this.g?.user?.wallets?.length) {
      this.getAllowances()
      this.loadCurrencies()
    } else {
      setTimeout(() => {
        if (this.g?.user?.wallets?.length) {
          this.getAllowances()
          this.loadCurrencies()
        } else {

          this.currencies = ['sats', 'USD', 'EUR']
        }
      }, 1000)
    }
  }
})