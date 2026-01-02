const { chromium } = require('playwright');

async function recordDemo() {
  console.log('Starting video recording demo...');

  const browser = await chromium.launch({
    headless: false,
    slowMo: 50
  });

  const context = await browser.newContext({
    recordVideo: {
      dir: './demo-videos/',
      size: { width: 1280, height: 720 }
    },
    viewport: { width: 1280, height: 720 }
  });

  const page = await context.newPage();

  try {
    // Scene 1: Dashboard
    console.log('Scene 1: Navigating to dashboard...');
    await page.goto('http://localhost:3000');
    await page.waitForSelector('table');
    await page.waitForTimeout(2000);

    // Scene 2: Sort by Risk Level
    console.log('Scene 2: Sorting by risk level...');
    await page.click('button:has-text("Risk Level")');
    await page.waitForTimeout(1500);

    // Scene 3: Click on first row's applicant link
    console.log('Scene 3: Opening an applicant...');
    const firstApplicantLink = page.locator('table tbody tr:first-child td:nth-child(2) a');
    await firstApplicantLink.click();
    await page.waitForTimeout(2000);

    // Scene 4: Scroll to show flags
    console.log('Scene 4: Scrolling to show flags...');
    await page.evaluate(() => window.scrollTo({ top: 400, behavior: 'smooth' }));
    await page.waitForTimeout(2000);

    // Scene 5: Scroll back up
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'smooth' }));
    await page.waitForTimeout(1000);

    // Scene 6: Toggle review status
    console.log('Scene 5: Toggling review status...');
    const checkbox = page.locator('input[type="checkbox"]');
    if (await checkbox.count() > 0) {
      await checkbox.first().click();
      await page.waitForTimeout(1500);
    }

    // Scene 7: Go back to list
    console.log('Scene 6: Going back to list...');
    await page.click('a:has-text("Back")');
    await page.waitForTimeout(2000);

    // Scene 8: Sort by flags
    console.log('Scene 7: Sorting by flags...');
    await page.click('button:has-text("Flags")');
    await page.waitForTimeout(1500);

    // Scene 9: Navigate to page 2
    console.log('Scene 8: Navigating to page 2...');
    await page.click('button:has-text("Next")');
    await page.waitForTimeout(1500);

    // Scene 10: Navigate to page 3
    console.log('Scene 9: Navigating to page 3...');
    await page.click('button:has-text("Next")');
    await page.waitForTimeout(1500);

    // Final pause
    await page.waitForTimeout(1000);

    console.log('Demo recording complete!');

  } catch (error) {
    console.error('Error during recording:', error.message);
  }

  // Close context to save video
  await context.close();
  await browser.close();

  console.log('Video saved to ./demo-videos/');
}

recordDemo().catch(console.error);
