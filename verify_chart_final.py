from playwright.sync_api import sync_playwright
import time

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto("http://localhost:3000")
            page.wait_for_selector(".js-plotly-plot", timeout=10000)

            # Find checkbox "nur individuelle Ergebnisse"
            checkbox_label = page.locator("label:has-text('nur individuelle Ergebnisse')")
            if checkbox_label.count() > 0:
                checkbox_label.click()

            time.sleep(2)
            page.screenshot(path="verification_final.png")
            print("Screenshot saved to verification_final.png")

        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    run()
