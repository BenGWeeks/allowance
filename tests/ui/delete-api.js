#!/usr/bin/env node
/**
 * Test Delete Allowance - API
 * Tests deleting allowances via direct API calls
 */

const { getConfig } = require('./auth-helper');

async function testDeleteAPI() {
  const config = getConfig();
  const apiKey = '2c3cd50a44784f19a4d7b4f605bbe247';

  console.log('🚀 Testing Allowance Deletion via API');
  console.log('==========================================');

  try {
    // Step 1: Get current allowances
    console.log('📋 Step 1: Getting current allowances...');

    const listResponse = await fetch(`${config.baseUrl}/allowance/api/v1/allowance`, {
      headers: { 'X-Api-Key': apiKey }
    });

    if (!listResponse.ok) {
      throw new Error(`Failed to list allowances: ${listResponse.status}`);
    }

    const allowances = await listResponse.json();
    console.log(`✓ Found ${allowances.length} allowances`);

    if (allowances.length === 0) {
      console.log('⚠️ No allowances to delete');
      return;
    }

    // Find a suitable allowance to delete (prefer the minutely test one)
    let targetAllowance = allowances.find(a => a.name.includes('Minutely')) || allowances[0];

    console.log(`🎯 Target for deletion: ${targetAllowance.name} (ID: ${targetAllowance.id})`);
    console.log(`   Amount: ${targetAllowance.amount} ${targetAllowance.currency}`);
    console.log(`   Address: ${targetAllowance.lightning_address}`);

    // Step 2: Delete the allowance
    console.log('\n🗑️ Step 2: Deleting allowance via API...');

    const deleteResponse = await fetch(`${config.baseUrl}/allowance/api/v1/allowance/${targetAllowance.id}`, {
      method: 'DELETE',
      headers: { 'X-Api-Key': apiKey }
    });

    console.log(`📤 DELETE request sent to: /allowance/api/v1/allowance/${targetAllowance.id}`);
    console.log(`📥 Response status: ${deleteResponse.status}`);

    if (deleteResponse.ok) {
      const result = await deleteResponse.json().catch(() => ({}));
      console.log('✅ Delete API call successful');
      console.log(`📄 Response: ${JSON.stringify(result, null, 2)}`);
    } else {
      const error = await deleteResponse.text();
      console.log(`❌ Delete failed: ${error}`);
    }

    // Step 3: Verify deletion
    console.log('\n🔍 Step 3: Verifying deletion...');

    const verifyResponse = await fetch(`${config.baseUrl}/allowance/api/v1/allowance`, {
      headers: { 'X-Api-Key': apiKey }
    });

    if (verifyResponse.ok) {
      const updatedAllowances = await verifyResponse.json();
      const stillExists = updatedAllowances.find(a => a.id === targetAllowance.id);

      console.log(`📊 Allowances after deletion: ${updatedAllowances.length}`);

      if (stillExists) {
        console.log('❌ FAILED: Allowance still exists after deletion!');
        console.log(`   Found: ${stillExists.name} (${stillExists.id})`);
        return false;
      } else {
        console.log('✅ SUCCESS: Allowance successfully deleted');
        console.log(`📉 Count reduced from ${allowances.length} to ${updatedAllowances.length}`);
        return true;
      }
    } else {
      console.log('❌ Could not verify deletion - API error');
      return false;
    }

  } catch (error) {
    console.error('❌ Test failed:', error.message);
    return false;
  }
}

// Step 4: Test deleting non-existent allowance
async function testDeleteNonExistent() {
  const config = getConfig();
  const apiKey = '2c3cd50a44784f19a4d7b4f605bbe247';
  const fakeId = 'nonexistent123456789';

  console.log('\n🚀 Testing deletion of non-existent allowance...');
  console.log(`🎯 Fake ID: ${fakeId}`);

  try {
    const deleteResponse = await fetch(`${config.baseUrl}/allowance/api/v1/allowance/${fakeId}`, {
      method: 'DELETE',
      headers: { 'X-Api-Key': apiKey }
    });

    console.log(`📥 Response status: ${deleteResponse.status}`);

    if (deleteResponse.status === 404) {
      console.log('✅ Correctly returned 404 for non-existent allowance');
      return true;
    } else if (deleteResponse.status === 200) {
      console.log('⚠️ API returned 200 for non-existent allowance (should be 404)');
      return false;
    } else {
      const error = await deleteResponse.text();
      console.log(`❌ Unexpected response: ${error}`);
      return false;
    }

  } catch (error) {
    console.error('❌ Test failed:', error.message);
    return false;
  }
}

// Run tests
async function runTests() {
  console.log('🧪 API Deletion Test Suite');
  console.log('==========================================\n');

  const results = [];

  // Test 1: Delete existing allowance
  const test1 = await testDeleteAPI();
  results.push({ name: 'Delete Existing Allowance', passed: test1 });

  // Test 2: Delete non-existent allowance
  const test2 = await testDeleteNonExistent();
  results.push({ name: 'Delete Non-existent Allowance', passed: test2 });

  // Summary
  console.log('\n==========================================');
  console.log('📊 TEST RESULTS SUMMARY');
  console.log('==========================================');

  const passed = results.filter(r => r.passed).length;
  const total = results.length;

  results.forEach(result => {
    console.log(`${result.passed ? '✅' : '❌'} ${result.name}`);
  });

  console.log(`\n📈 Overall: ${passed}/${total} tests passed`);

  if (passed === total) {
    console.log('🎉 ALL API DELETION TESTS PASSED!');
    process.exit(0);
  } else {
    console.log('❌ Some API deletion tests failed');
    process.exit(1);
  }
}

// Run if called directly
if (require.main === module) {
  runTests();
}

module.exports = { testDeleteAPI, testDeleteNonExistent };