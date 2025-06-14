/* globals Quasar, Vue, _, LNbits, LOCALE */

// Minimal Vue app without windowMixin to test form submission
window.app = Vue.createApp({
  data() {
    return {
      allowances: [],
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
      ],
      // Mock user data
      g: {
        user: {
          wallets: [
            {id: 'test-wallet', name: 'Test Wallet', adminkey: 'test-admin-key', inkey: 'test-in-key'}
          ]
        }
      }
    }
  },
  methods: {
    openCreateDialog() {
      const today = new Date().toISOString().split('T')[0]
      this.formDialog.data = {
        wallet: this.g.user.wallets[0].id,
        currency: 'sats',
        active: true,
        start_date: today
      }
      this.formDialog.show = true
      console.log('📅 Form opened with default start date:', today)
    },
    
    saveAllowance() {
      console.log('🔥 saveAllowance called (minimal version)')
      console.log('📊 Form data:', this.formDialog.data)
      
      // Simple validation
      if (!this.formDialog.data.name) {
        console.log('❌ Missing name')
        return
      }
      
      console.log('✅ Form validation passed')
      console.log('🎯 Would create allowance:', this.formDialog.data)
      
      // Close dialog to simulate success
      this.formDialog.show = false
      this.formDialog.data = {}
      
      console.log('✅ Dialog closed - form submission successful!')
    },
    
    closeFormDialog() {
      this.formDialog.show = false
      this.formDialog.data = {}
    }
  },
  
  mounted() {
    console.log('🎯 Minimal Vue app mounted successfully!')
  }
}).mount('#vue')