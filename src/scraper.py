import time
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager


def scrape_hmc_courses(url, output_file):
    """
    Scrapes HMC course description pages for prerequisites and details.
    """
   
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in background
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Set a window size to ensure elements are "visible" for clicking
    chrome_options.add_argument("--window-size=1920,1080")


    print(f"Initializing Browser...")
    # specific service setup to handle driver installation automatically
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)


    try:
        print(f"Navigating to: {url}")
        driver.get(url)


        # Wait for the main list to load
        wait = WebDriverWait(driver, 10)
       
        # Locate all the course toggle links (the aria buttons)
        # Based on the HTML provided: class="wp-block-mudd-acalog-widget-courses-course-link"
        course_links = wait.until(EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, "a.wp-block-mudd-acalog-widget-courses-course-link")
        ))
       
        print(f"Found {len(course_links)} courses. Starting extraction...")


        with open(output_file, "w", encoding="utf-8") as f:
           
            # We iterate by index because clicking elements might refresh parts of the DOM
            # causing "StaleElementReferenceException" if we hold onto the element objects
            for i in range(len(course_links)):
                try:
                    # Re-find the list to avoid stale elements
                    current_links = driver.find_elements(By.CSS_SELECTOR, "a.wp-block-mudd-acalog-widget-courses-course-link")
                    if i >= len(current_links):
                        break
                   
                    link = current_links[i]
                   
                    # Get the target ID (e.g., #course-03ncg) to know what to wait for
                    target_id = link.get_attribute("data-bs-target")
                    course_title = link.text.strip()
                   
                    # Attempt to find the course code (sibling span)
                    # Structure: <span>CODE</span><span><a ...>Title</a></span>
                    try:
                        parent_span = link.find_element(By.XPATH, "./..")
                        grandparent_div = parent_span.find_element(By.XPATH, "./..")
                        course_code = grandparent_div.find_element(By.TAG_NAME, "span").text.strip()
                    except:
                        course_code = "UNKNOWN"


                    print(f"Processing: {course_code} - {course_title}")


                    # Scroll to element to ensure it's clickable
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
                    time.sleep(0.5) # Short buffer for scroll to settle


                    # Click to expand (Trigger AJAX)
                    # Using JS click is often safer for these types of overlay widgets
                    driver.execute_script("arguments[0].click();", link)


                    # Wait for the body to become visible and contain text
                    # The content loads into a div with class 'acalog-course-body' inside the target_id
                    body_selector = f"{target_id} .acalog-course-body"
                   
                    try:
                        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, body_selector)))
                    except TimeoutException:
                        # Sometimes it's already loaded or takes longer
                        print(f"  Warning: Timeout waiting for details on {course_code}")
                        continue


                    # Extract the content div
                    content_div = driver.find_element(By.CSS_SELECTOR, body_selector)
                   
                    # Get all paragraphs to format them nicely
                    paragraphs = content_div.find_elements(By.TAG_NAME, "p")
                   
                    # Format output for this course
                    f.write(f"Course: {course_code} {course_title}\n")
                    f.write("-" * 40 + "\n")
                   
                    for p in paragraphs:
                        # Get text and clean it up
                        text = p.text.strip()
                        # If the text is empty, skip
                        if not text:
                            continue
                        f.write(f"{text}\n")
                   
                    f.write("\n" + "="*40 + "\n\n")
                   
                    # Optional: Collapse it back to keep DOM clean, though not strictly necessary
                    # driver.execute_script("arguments[0].click();", link)
                   
                except Exception as e:
                    print(f"Error processing course index {i}: {e}")
                    continue


        print(f"Done! Data saved to {output_file}")


    except Exception as main_e:
        print(f"Critical Error: {main_e}")
    finally:
        driver.quit()


if __name__ == "__main__":
    # Default URL if none provided
    target_url = "https://www.hmc.edu/biology/programs/courses/"
   
    # Allow command line argument for different pages
    if len(sys.argv) > 1:
        target_url = sys.argv[1]
       
    output_filename = "course_prerequisites.txt"

    if len(sys.argv) > 2:
        output_filename = sys.argv[2]

    scrape_hmc_courses(target_url, output_filename)