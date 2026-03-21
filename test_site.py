from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    print("Launching Chromium browser...")
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    print("Navigating to http://127.0.0.1:5000/login ...")
    page.goto('http://127.0.0.1:5000/login', wait_until='networkidle')
    
    print("Page title:", page.title())
    
    # Take a screenshot before action
    page.screenshot(path='login_before.png', full_page=True)
    print("Screenshot saved to login_before.png")

    # Attempt to login
    print("Filling login form...")
    page.fill('input#username', 'testuser')
    page.fill('input#password', 'testpassword')
    page.click('button.login-btn')
    
    # Wait for the next state
    page.wait_for_load_state('networkidle')
    print("Page title after attempt:", page.title())
    
    # Take a screenshot after action
    page.screenshot(path='login_after.png', full_page=True)
    print("Screenshot saved to login_after.png")
    
    browser.close()
    print("Test finished successfully!")
