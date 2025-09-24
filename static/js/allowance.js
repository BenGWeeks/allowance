/* globals Quasar, Vue, _, windowMixin, LNbits, LOCALE */

window.app = Vue.createApp({
  el: '#vue',
  mixins: [window.windowMixin],
  data() {
    return {
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
      // For datetime-local input, we need YYYY-MM-DDTHH:MM format
      const now = new Date().toISOString().slice(0, 16)
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
      // start_datetime is optional - backend will default to now() if not provided
      
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
        LNbits.utils.notifyApiError('Form validation failed: ' + errors.join(', '))
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
      
      // Set start_datetime to current date if not specified
      if (!data.start_datetime) {
        data.start_datetime = new Date().toISOString().split('T')[0]
        console.log('📅 Set start_datetime to:', data.start_datetime)
      }
      
      // Transform data to match backend model
      console.log('🔥 Processing active field:', data.active, '(type:', typeof data.active, ')')
      
      const backendData = {
        id: data.id,
        name: data.name,  // Keep name field as expected by backend
        memo: data.name,  // Also include memo field
        wallet: data.wallet,
        lightning_address: data.lightning_address,
        amount: parseInt(data.amount),
        currency: data.currency || 'sats',
        frequency_type: data.frequency_type,
        start_datetime: new Date(data.start_datetime).toISOString(),  // Convert to ISO datetime
        next_payment_date: this.calculateNextPaymentDate(data.start_datetime, data.frequency_type),
        active: Boolean(data.active),  // Ensure boolean type
        end_datetime: data.end_datetime ? new Date(data.end_datetime).toISOString() : null
      }
      
      console.log('🔥 Backend data active field:', backendData.active, '(type:', typeof backendData.active, ')')
      
      // For minutely payments, set end date based on duration
      if (data.frequency_type === 'minutely') {
        // Default to 5 minutes for testing
        const endDate = new Date(data.start_datetime)
        endDate.setMinutes(endDate.getMinutes() + 5)
        backendData.end_datetime = endDate.toISOString()
      }
      
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
        amount: clonedData.amount,
        currency: clonedData.currency,
        frequency_type: clonedData.frequency_type,
        start_datetime: clonedData.start_datetime, // Add missing start_datetime
        next_payment_date: clonedData.next_payment_date,
        memo: clonedData.memo,
        end_datetime: clonedData.end_datetime
      }
      
      console.log('📋 After cloning:', this.formDialog.data)
      
      // Ensure start_datetime is in proper format for datetime-local input
      if (this.formDialog.data.start_datetime) {
        try {
          // Handle timestamps with microseconds (e.g., 2025-09-26T21:34:43.595856)
          let dateStr = this.formDialog.data.start_datetime

          // Check if it has timezone info (Z or +/-offset)
          const hasTimezone = dateStr.includes('Z') || /[+-]\d{2}:\d{2}$/.test(dateStr)

          // Remove microseconds if present (keep only up to milliseconds)
          if (dateStr.includes('.')) {
            const parts = dateStr.split('.')
            if (parts[1].length > 3) {
              // Keep only 3 digits for milliseconds
              const beforeDot = parts[0]
              const afterDot = parts[1].substring(0, 3)
              // Add back timezone if it existed
              dateStr = beforeDot + '.' + afterDot + (hasTimezone ? '' : 'Z')
            } else if (!hasTimezone) {
              dateStr += 'Z'
            }
          } else if (!hasTimezone) {
            dateStr += 'Z'
          }

          const date = new Date(dateStr)
          // Format for datetime-local: YYYY-MM-DDTHH:MM
          if (!isNaN(date.getTime())) {
            this.formDialog.data.start_datetime = date.toISOString().slice(0, 16)
            console.log('📅 Converted start_datetime to:', this.formDialog.data.start_datetime)
          } else {
            console.warn('⚠️ Could not parse start_datetime:', this.formDialog.data.start_datetime)
          }
        } catch (e) {
          console.error('❌ Error parsing start_datetime:', e)
        }
      }

      // Ensure end_datetime is in proper format for datetime-local input
      if (this.formDialog.data.end_datetime) {
        try {
          // Handle timestamps with microseconds
          let dateStr = this.formDialog.data.end_datetime

          // Check if it has timezone info (Z or +/-offset)
          const hasTimezone = dateStr.includes('Z') || /[+-]\d{2}:\d{2}$/.test(dateStr)

          // Remove microseconds if present (keep only up to milliseconds)
          if (dateStr.includes('.')) {
            const parts = dateStr.split('.')
            if (parts[1].length > 3) {
              // Keep only 3 digits for milliseconds
              const beforeDot = parts[0]
              const afterDot = parts[1].substring(0, 3)
              // Add back timezone if it existed
              dateStr = beforeDot + '.' + afterDot + (hasTimezone ? '' : 'Z')
            } else if (!hasTimezone) {
              dateStr += 'Z'
            }
          } else if (!hasTimezone) {
            dateStr += 'Z'
          }

          const date = new Date(dateStr)
          // Format for datetime-local: YYYY-MM-DDTHH:MM
          if (!isNaN(date.getTime())) {
            this.formDialog.data.end_datetime = date.toISOString().slice(0, 16)
            console.log('📅 Converted end_datetime to:', this.formDialog.data.end_datetime)
          } else {
            console.warn('⚠️ Could not parse end_datetime:', this.formDialog.data.end_datetime)
          }
        } catch (e) {
          console.error('❌ Error parsing end_datetime:', e)
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
  watch: {
    'formDialog.data.currency': function(newVal) {
      if (newVal) {
        this.updateFiatRate(newVal)
      }
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