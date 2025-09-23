#!/usr/bin/env node
/**
 * Monitor Payment Test
 * Monitors for actual payments from the minutely allowance
 */

const { getConfig } = require('./auth-helper');

async function monitorPayments() {
  const config = getConfig();
  const apiKey = '2c3cd50a44784f19a4d7b4f605bbe247';
  const allowanceId = 'nTc63dqu76DwdoygFUgvK5';

  console.log('🚀 Starting Payment Monitoring');
  console.log('==========================================');
  console.log(`⏰ Start time: ${new Date().toISOString()}`);
  console.log(`🎯 Monitoring allowance: ${allowanceId}`);
  console.log(`💰 Expected: 5 sats per minute for 10 minutes`);
  console.log('==========================================\n');

  const startTime = Date.now();
  const duration = 10 * 60 * 1000; // 10 minutes
  let paymentCount = 0;
  let lastTransactionTime = null;

  while (Date.now() - startTime < duration) {
    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    const minutes = Math.floor(elapsed / 60);
    const seconds = elapsed % 60;

    console.log(`\n⏱️ ${minutes}:${seconds.toString().padStart(2, '0')} - Checking for payments...`);

    try {
      // Check payments via API
      const response = await fetch(`${config.baseUrl}/api/v1/payments`, {
        headers: { 'X-Api-Key': apiKey }
      });

      if (response.ok) {
        const payments = response.json ? await response.json() : [];

        // Look for outgoing payments with our memo
        const allowancePayments = payments.filter(p =>
          p.amount < 0 &&
          p.memo &&
          p.memo.includes('Testing minutely payments')
        );

        if (allowancePayments.length > paymentCount) {
          const newPayments = allowancePayments.length - paymentCount;
          paymentCount = allowancePayments.length;
          lastTransactionTime = allowancePayments[0].time;

          console.log(`💰 NEW PAYMENT(S) DETECTED! Total: ${paymentCount}`);
          console.log(`   Latest: ${allowancePayments[0].amount} sats at ${lastTransactionTime}`);
          console.log(`   Memo: ${allowancePayments[0].memo}`);
        } else {
          console.log(`⏳ No new payments (Total so far: ${paymentCount})`);
        }

        // Check allowance status
        const statusResponse = await fetch(`${config.baseUrl}/allowance/api/v1/allowance/${allowanceId}`, {
          headers: { 'X-Api-Key': apiKey }
        });

        if (statusResponse.ok) {
          const allowance = await statusResponse.json();
          console.log(`📊 Allowance status: ${allowance.active ? 'Active' : 'Inactive'}`);
          console.log(`📅 Next payment: ${allowance.next_payment_date}`);
          console.log(`📅 End time: ${allowance.end_datetime}`);
        }

      } else {
        console.log(`❌ API Error: ${response.status}`);
      }

    } catch (error) {
      console.log(`❌ Error: ${error.message}`);
    }

    // Wait 30 seconds before next check
    if (Date.now() - startTime < duration) {
      await new Promise(resolve => setTimeout(resolve, 30000));
    }
  }

  console.log('\n' + '=' * 50);
  console.log('📊 FINAL MONITORING RESULTS');
  console.log('=' * 50);
  console.log(`⏰ Total monitoring time: 10 minutes`);
  console.log(`💰 Total payments detected: ${paymentCount}`);
  console.log(`📅 Last payment time: ${lastTransactionTime || 'None'}`);

  if (paymentCount > 0) {
    console.log('✅ SUCCESS: Payments are being processed!');
    console.log(`📈 Average: ${paymentCount / 10} payments per minute`);
  } else {
    console.log('❌ FAILURE: No payments were made');
    console.log('🔍 This indicates the scheduler is not running or payments are failing');
  }

  return paymentCount > 0;
}

// Run if called directly
if (require.main === module) {
  monitorPayments()
    .then(success => {
      process.exit(success ? 0 : 1);
    })
    .catch(error => {
      console.error('❌ Monitoring failed:', error);
      process.exit(1);
    });
}

module.exports = { monitorPayments };