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
          {name: 'id', align: 'left', label: 'ID', field: 'id'},
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
      if (!this.g?.user?.wallets?.length) {
        console.log('No user wallets available')
        return
      }
      this.allowanceTable.loading = true
      LNbits.api
        .request(
          'GET',
          '/allowance/api/v1/allowance',
          this.g.user.wallets[0].inkey
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
      const today = new Date().toISOString().split('T')[0]
      this.formDialog.data = {
        wallet: this.g.user.wallets[0].id,
        currency: 'sats',
        frequency_type: 'weekly', // Default to weekly to help with testing
        active: true,
        start_date: today
      }
      this.formDialog.show = true
      console.log('📅 Form opened with default start date:', today)
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
      
      // Validate required fields
      const errors = []
      if (!this.formDialog.data.name) errors.push('Description is required')
      if (!this.formDialog.data.wallet) errors.push('Wallet is required') 
      if (!this.formDialog.data.lightning_address) errors.push('Lightning address is required')
      if (!this.formDialog.data.amount || this.formDialog.data.amount <= 0) errors.push('Amount must be greater than 0')
      if (!this.formDialog.data.frequency_type) errors.push('Frequency is required')
      if (!this.formDialog.data.start_date) errors.push('Start date is required')
      
      console.log('🔍 Validation check:', {
        name: this.formDialog.data.name,
        wallet: this.formDialog.data.wallet,
        lightning_address: this.formDialog.data.lightning_address,
        amount: this.formDialog.data.amount,
        frequency_type: this.formDialog.data.frequency_type,
        start_date: this.formDialog.data.start_date,
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
      
      // Set start_date to current date if not specified
      if (!data.start_date) {
        data.start_date = new Date().toISOString().split('T')[0]
        console.log('📅 Set start_date to:', data.start_date)
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
        start_date: new Date(data.start_date).toISOString(),  // Convert to ISO datetime
        next_payment_date: this.calculateNextPaymentDate(data.start_date, data.frequency_type),
        active: Boolean(data.active),  // Ensure boolean type
        end_date: data.end_date ? new Date(data.end_date).toISOString() : null
      }
      
      console.log('🔥 Backend data active field:', backendData.active, '(type:', typeof backendData.active, ')')
      
      // For minutely payments, set end date based on duration
      if (data.frequency_type === 'minutely') {
        // Default to 5 minutes for testing
        const endDate = new Date(data.start_date)
        endDate.setMinutes(endDate.getMinutes() + 5)
        backendData.end_date = endDate.toISOString()
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
        start_date: clonedData.start_date, // Add missing start_date
        next_payment_date: clonedData.next_payment_date,
        memo: clonedData.memo,
        end_date: clonedData.end_date
      }
      
      console.log('📋 After cloning:', this.formDialog.data)
      
      // Ensure start_date is in proper format for date input
      if (this.formDialog.data.start_date) {
        const date = new Date(this.formDialog.data.start_date)
        this.formDialog.data.start_date = date.toISOString().split('T')[0]
        console.log('📅 Converted start_date to:', this.formDialog.data.start_date)
      } else {
        // Default to today if no start_date exists
        const today = new Date().toISOString().split('T')[0]
        this.formDialog.data.start_date = today
        console.log('📅 No start_date found, defaulted to today:', today)
      }
      
      // Ensure end_date is in proper format for date input if it exists
      if (this.formDialog.data.end_date) {
        const endDate = new Date(this.formDialog.data.end_date)
        this.formDialog.data.end_date = endDate.toISOString().split('T')[0]
        console.log('📅 Converted end_date to:', this.formDialog.data.end_date)
      }
      
      // Set active field separately to ensure proper reactivity
      const originalActive = row.active
      
      // Force active to true for editing (since we're editing an existing allowance)
      // More robust boolean conversion but default to true for edits
      let activeValue = true  // Default for editing
      
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
      console.log('  Forced to true for editing:', activeValue)
      
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