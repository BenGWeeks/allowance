/* globals Quasar, Vue, _, windowMixin, LNbits, LOCALE */

window.app = Vue.createApp({
  el: '#vue',
  mixins: [window.windowMixin],
  data() {
    return {
      // Detect user's locale for date formatting
      userLocale: navigator.language || 'en-GB',
      allowances: [],
      currencies: [],
      fiatRates: {},
      allowanceTable: {
        columns: [
          {name: 'name', align: 'left', label: 'Description', field: 'name'},
          {name: 'amount', align: 'right', label: 'Amount', field: 'amount'},
          {name: 'lightning_address', align: 'left', label: 'Recipient', field: 'lightning_address'},
          {name: 'frequency_type', align: 'left', label: 'Frequency', field: 'frequency_type'},
          {name: 'status', align: 'center', label: 'Status', field: 'active'}
        ],
        pagination: {
          rowsPerPage: 10
        },
        loading: false
      },
      formDialog: {
        show: false,
        loading: false,
        data: {}
      },
      frequencyOptions: [
        {label: 'Minutely', value: 'minutely'},
        {label: 'Hourly', value: 'hourly'},
        {label: 'Weekly', value: 'weekly'},
        {label: 'Monthly', value: 'monthly'},
        {label: 'Yearly', value: 'yearly'}
      ]
    }
  },
  methods: {
    getAllowances() {
      console.log('🔍 Loading allowances...')
      this.allowanceTable.loading = true
      
      // Use the first available wallet for admin operations
      const wallet = this.g.user.wallets[0]
      if (!wallet) {
        console.error('❌ No wallet found for authentication')
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
          console.log('✅ Allowances loaded:', response.data)
          // Log first allowance to see what fields are available
          if (response.data && response.data.length > 0) {
            console.log('📊 First allowance fields:', Object.keys(response.data[0]))
            console.log('📅 First allowance start_datetime:', response.data[0].start_datetime)
            console.log('📅 First allowance end_datetime:', response.data[0].end_datetime)
          }
          this.allowances = response.data
        })
        .catch(err => {
          console.error('❌ Error loading allowances:', err)
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
      // For datetime-local input, we need YYYY-MM-DDTHH:MM format in LOCAL time
      const now = this.toLocalDatetimeString(new Date())
      this.formDialog.data = {
        wallet: this.g.user.wallets[0].id,
        currency: 'sats',
        frequency_type: 'weekly', // Default to weekly to help with testing
        active: true,
        start_datetime: now
      }
      this.formDialog.show = true
      console.log('📅 Form opened with default start datetime:', now)
      console.log('🔘 Active state set to:', this.formDialog.data.active)
    },
    saveAllowance(event) {
      // Prevent default form submission like LNURLP pattern
      if (event) {
        event.preventDefault()
      }
      
      console.log('🔥 saveAllowance called')
      console.log('📊 Form data:', this.formDialog.data)
      console.log('🔘 Active field at submission:', this.formDialog.data.active, '(type:', typeof this.formDialog.data.active, ')')
      
      // Don't proceed if dialog is not shown
      if (!this.formDialog.show) {
        console.log('❌ Form dialog is not visible, aborting saveAllowance')
        return
      }
      
      // Validate required fields
      const errors = []
      if (!this.formDialog.data.name) errors.push('Description is required')
      if (!this.formDialog.data.wallet) errors.push('Wallet is required')
      if (!this.formDialog.data.lightning_address) errors.push('Lightning address is required')
      if (!this.formDialog.data.amount || this.formDialog.data.amount <= 0) errors.push('Amount must be greater than 0')
      if (!this.formDialog.data.frequency_type) errors.push('Frequency is required')
      if (!this.formDialog.data.start_datetime) errors.push('Start date & time is required')

      // Validate: end_datetime must be after start_datetime
      if (this.formDialog.data.end_datetime && this.formDialog.data.start_datetime) {
        const startDate = new Date(this.formDialog.data.start_datetime)
        const endDate = new Date(this.formDialog.data.end_datetime)
        if (endDate <= startDate) {
          errors.push('End date must be after start date')
        }
      }

      // Validate: cannot activate if end_datetime is in the past
      if (this.formDialog.data.active && this.formDialog.data.end_datetime) {
        const endDate = new Date(this.formDialog.data.end_datetime)
        const now = new Date()
        if (endDate < now) {
          errors.push('Cannot activate allowance: end date is in the past')
        }
      }
      
      console.log('🔍 Validation check:', {
        name: this.formDialog.data.name,
        wallet: this.formDialog.data.wallet,
        lightning_address: this.formDialog.data.lightning_address,
        amount: this.formDialog.data.amount,
        frequency_type: this.formDialog.data.frequency_type,
        start_datetime: this.formDialog.data.start_datetime,
        errors: errors
      })
      
      if (errors.length > 0) {
        console.log('❌ Validation errors:', errors)
        this.$q.notify({
          type: 'negative',
          message: 'Validation failed: ' + errors.join(', '),
          timeout: 5000,
          position: 'top'
        })
        return
      }
      
      console.log('✅ Validation passed, proceeding...')
      
      console.log('🔍 Available wallets:', this.g.user.wallets)
      console.log('🔍 Looking for wallet ID:', this.formDialog.data.wallet)
      
      const wallet = _.findWhere(this.g.user.wallets, {
        id: this.formDialog.data.wallet
      })
      console.log('💰 Selected wallet:', wallet)
      
      if (!wallet) {
        console.log('❌ No wallet found')
        LNbits.utils.notifyApiError('No wallet selected')
        return
      }
      
      console.log('✅ Wallet found, preparing data...')

      const data = _.clone(this.formDialog.data)
      
      // Transform data to match backend model
      console.log('🔥 Processing active field:', data.active, '(type:', typeof data.active, ')')

      // Don't convert currency amounts here - conversion happens at payment time
      let amount = parseFloat(data.amount) || 0

      // For sats, ensure integer
      if (!data.currency || data.currency === 'sats' || data.currency === 'satoshis') {
        amount = Math.round(amount)
      }
      // For fiat currencies, keep the decimal amount as-is (e.g., 0.02 for GBP)

      const backendData = {
        id: data.id,
        name: data.name,  // Keep name field as expected by backend
        memo: data.name,  // Also include memo field
        wallet: data.wallet,
        lightning_address: data.lightning_address,
        amount: amount,  // Store the original amount (0.02 for GBP, 10 for sats)
        currency: data.currency || 'sats',
        active: Boolean(data.active),  // Ensure boolean type
        end_datetime: data.end_datetime ? new Date(data.end_datetime).toISOString() : null
      }

      // Only include start_datetime and frequency_type when creating (not updating)
      // These fields are locked after creation
      if (!data.id) {
        backendData.frequency_type = data.frequency_type
        backendData.start_datetime = data.start_datetime ? new Date(data.start_datetime).toISOString() : new Date().toISOString()
        backendData.next_payment_date = this.calculateNextPaymentDate(data.start_datetime, data.frequency_type)
      }
      
      console.log('🔥 Backend data active field:', backendData.active, '(type:', typeof backendData.active, ')')
      console.log('📤 Final data to send:', backendData)
      console.log('🔍 Decision point - has ID?', !!backendData.id, 'ID value:', backendData.id)
      
      if (backendData.id) {
        console.log('🔄 Updating existing allowance')
        this.updateAllowance(wallet, backendData)
      } else {
        console.log('➕ Creating new allowance')
        this.createAllowance(wallet, backendData)
      }
    },
    createAllowance(wallet, data) {
      console.log('🚀 createAllowance called with:', { wallet, data })
      this.formDialog.loading = true
      console.log('📡 Making POST request...')
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
    openUpdateDialog(row) {
      console.log('🔄 openUpdateDialog called with row:', row)
      console.log('🔍 Row active field:', row.active, '(type:', typeof row.active, ')')
      console.log('📅 Row start_datetime:', row.start_datetime)
      console.log('📅 Row end_datetime:', row.end_datetime)

      // Reset form dialog first
      this.formDialog.data = {}

      // Deep clone the row data to avoid reference issues
      const clonedData = JSON.parse(JSON.stringify(row))

      // Set data piece by piece to ensure reactivity
      this.formDialog.data = {
        id: clonedData.id,
        name: clonedData.name,
        wallet: clonedData.wallet,
        lightning_address: clonedData.lightning_address,
        amount: clonedData.amount,  // Amount is already in the correct format (0.02 for GBP, 10 for sats)
        currency: clonedData.currency,
        frequency_type: clonedData.frequency_type,
        start_datetime: clonedData.start_datetime, // Add missing start_datetime
        next_payment_date: clonedData.next_payment_date,
        memo: clonedData.memo,
        end_datetime: clonedData.end_datetime
      }
      
      console.log('📋 After cloning:', this.formDialog.data)

      // Convert datetime fields from UTC (API) to local time (for display)
      // API returns ISO strings like "2025-09-28T07:49:00+00:00" in UTC
      // datetime-local input needs local time in "YYYY-MM-DDTHH:mm" format
      if (this.formDialog.data.start_datetime) {
        if (typeof this.formDialog.data.start_datetime === 'string') {
          const utcDate = new Date(this.formDialog.data.start_datetime)
          this.formDialog.data.start_datetime = this.toLocalDatetimeString(utcDate)
          console.log('✅ Converted start_datetime to local:', this.formDialog.data.start_datetime)
        }
      }

      if (this.formDialog.data.end_datetime) {
        if (typeof this.formDialog.data.end_datetime === 'string') {
          const utcDate = new Date(this.formDialog.data.end_datetime)
          this.formDialog.data.end_datetime = this.toLocalDatetimeString(utcDate)
          console.log('✅ Converted end_datetime to local:', this.formDialog.data.end_datetime)
        }
      }
      
      // Set active field separately to ensure proper reactivity
      const originalActive = row.active

      // Convert active field to boolean value
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
      
      // Set active with Vue.set to ensure reactivity (Vue 3 compatibility)
      this.$set ? this.$set(this.formDialog.data, 'active', activeValue) : (this.formDialog.data.active = activeValue)
      
      console.log('🔘 Active conversion:')
      console.log('  Original value:', originalActive, '(type:', typeof originalActive, ')')
      console.log('  Converted to:', this.formDialog.data.active, '(type:', typeof this.formDialog.data.active, ')')
      
      console.log('✅ Final form data:', JSON.stringify(this.formDialog.data, null, 2))
      this.formDialog.show = true
      
      // Force Vue to update and ensure toggle reflects the active state
      this.$nextTick(() => {
        console.log('🔄 Vue nextTick - form data:', this.formDialog.data)
        console.log('🔄 Vue nextTick - active value:', this.formDialog.data.active)
        
        // Force reactivity update for the active field
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
            console.log(`💱 Rate for ${currency}: 1 ${currency} = ${response.data.rate} sats`)
          })
          .catch(err => {
            console.error(`Failed to get rate for ${currency}:`, err)
          })
      }
    },
    toggleActive() {
      console.log('🔄 Manual toggle called - before:', this.formDialog.data.active)
      this.formDialog.data.active = !this.formDialog.data.active
      console.log('🔄 Manual toggle called - after:', this.formDialog.data.active)
      this.$forceUpdate()
    },
    formatErrorTime(timestamp) {
      if (!timestamp) return ''

      let date

      // Handle different timestamp formats
      if (typeof timestamp === 'string') {
        // Try parsing as ISO datetime string first
        date = new Date(timestamp)

        // If that fails, try as Unix timestamp (seconds)
        if (isNaN(date.getTime())) {
          const ts = parseInt(timestamp)
          if (!isNaN(ts) && ts > 0) {
            date = new Date(ts * 1000)
          }
        }
      } else if (typeof timestamp === 'number') {
        // Unix timestamp (seconds)
        date = new Date(timestamp * 1000)
      } else {
        return 'Invalid datetime'
      }

      // Check if date is valid
      if (!date || isNaN(date.getTime())) return 'Invalid datetime'

      const now = new Date()
      const diff = now - date

      // Show relative time for recent errors
      const minutes = Math.floor(diff / 60000)
      const hours = Math.floor(diff / 3600000)
      const days = Math.floor(diff / 86400000)

      if (minutes < 1) return 'Just now'
      if (minutes < 60) return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`
      if (hours < 24) return `${hours} hour${hours !== 1 ? 's' : ''} ago`
      if (days < 7) return `${days} day${days !== 1 ? 's' : ''} ago`

      // Show full date for older errors
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
    formatDatetime(timestamp) {
      // Format a datetime for display in tooltips
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
    calculateNextPaymentDate(startDate, frequencyType) {
      const date = new Date(startDate)

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
      console.log('🌍 Loading currencies from LNbits core API...')
      
      // Try without authentication first (public endpoint)
      LNbits.api
        .request('GET', '/api/v1/currencies')
        .then(response => {
          console.log('✅ Currencies loaded successfully:', response.data?.length || 0, 'currencies')
          this.currencies = ['sats', ...response.data]
        })
        .catch(err => {
          console.warn('⚠️ Public currencies API failed, trying with authentication...', err.message || err)
          
          // Try with authentication as fallback
          if (this.g?.user?.wallets?.[0]?.inkey) {
            LNbits.api
              .request('GET', '/api/v1/currencies', this.g.user.wallets[0].inkey)
              .then(response => {
                console.log('✅ Currencies loaded with auth:', response.data?.length || 0, 'currencies')
                this.currencies = ['sats', ...response.data]
              })
              .catch(authErr => {
                console.error('❌ Failed to fetch currencies with auth:', authErr.message || authErr)
                console.log('💡 Falling back to basic currencies')
                this.currencies = ['sats', 'USD', 'EUR']
              })
          } else {
            console.error('❌ Failed to fetch currencies and no auth available:', err.message || err)
            console.log('💡 Falling back to basic currencies')
            this.currencies = ['sats', 'USD', 'EUR']
          }
        })
    }
  },
  computed: {
    isEndDateInPast() {
      if (!this.formDialog.data.end_datetime) {
        return false
      }
      const endDate = new Date(this.formDialog.data.end_datetime)
      const now = new Date()
      return endDate < now
    }
  },
  watch: {
    'formDialog.data.currency': function(newVal) {
      if (newVal) {
        this.updateFiatRate(newVal)
      }
    },
    'formDialog.data.end_datetime': function(newVal) {
      // Automatically deactivate if end_datetime is in the past
      if (newVal && newVal.trim() !== '') {
        const endDate = new Date(newVal)
        const now = new Date()
        if (endDate < now) {
          console.log('⚠️ End date is in the past, deactivating allowance')
          this.formDialog.data.active = false
        }
      }
      // If end_datetime is cleared or in the future, user can freely toggle active
    }
  },
  created() {
    if (this.g?.user?.wallets?.length) {
      this.getAllowances()
      this.loadCurrencies()
    } else {
      // If user data not loaded yet, retry after a short delay
      setTimeout(() => {
        if (this.g?.user?.wallets?.length) {
          this.getAllowances()
          this.loadCurrencies()
        } else {
          console.warn('User data still not available, loading basic currencies only')
          this.currencies = ['sats', 'USD', 'EUR']
        }
      }, 1000)
    }
  }
})