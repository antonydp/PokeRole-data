import requests
from bs4 import BeautifulSoup
import json

def scrape_pokemon_ribbons(url):
    """
    Scrapes Pokémon ribbon data (image URL, name, description) from a given URL.

    Args:
        url (str): The URL of the Serebii.net ribbons page.

    Returns:
        list: A list of dictionaries, where each dictionary represents a ribbon
              with its 'name', 'image_url', and 'description'.
              Returns an empty list if scraping fails.
    """
    ribbons_data = []
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find the main table containing ribbon information
        ribbon_table = soup.find('table', class_='dextable')

        if not ribbon_table:
            print("Error: Could not find the ribbon table.")
            return []

        # Iterate through each row in the table (skipping the header row)
        rows = ribbon_table.find_all('tr')[1:]  # Skip the header row

        for row in rows:
            columns = row.find_all('td')
            if len(columns) >= 3:  # Ensure there are enough columns for image, name, and description
                image_column = columns[0]
                name_column = columns[1]
                description_column = columns[2]

                # Extract image URL
                img_tag = image_column.find('img')
                if img_tag and 'src' in img_tag.attrs:
                    image_url = img_tag['src']
                    # Serebii uses relative URLs, so we need to make them absolute
                    if not image_url.startswith('http'):
                        image_url = "https://www.serebii.net/games/" + image_url
                else:
                    image_url = None

                # Extract name
                name = name_column.get_text(strip=True)

                # Extract description
                description = description_column.get_text(separator=' ', strip=True)

                ribbons_data.append({
                    'name': name,
                    'image_url': image_url,
                    'description': description
                })

    except requests.exceptions.RequestException as e:
        print(f"Error making request to {url}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    return ribbons_data

def scrape_gym_badges(url):
    """
    Scrapes Pokémon Gym Badge data (name, image URL, full description) from a Fandom Wiki page.

    Args:
        url (str): The URL of the Pokémon Fandom Wiki Gym Badges page.

    Returns:
        list: A list of dictionaries, where each dictionary represents a Gym Badge
              with its 'name', 'image_url', and a more complete 'description'.
              Returns an empty list if scraping fails.
    """
    badges_data = []
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find all prettytable elements, which contain the badge information
        # Exclude the "Anime exclusive" tables for now, as their structure might differ slightly
        content_tables = soup.find_all('table', class_='prettytable')

        # Filter out the "Anime exclusive" section for structured data
        # We'll stop processing tables once we hit the "Anime exclusive" heading
        anime_exclusive_heading = soup.find('h2', id='Anime_exclusive')

        relevant_tables = []
        if anime_exclusive_heading:
            # Get all elements between the first league heading and the anime exclusive heading
            start_element = soup.find('h2', id='Indigo_League')
            if start_element:
                current_element = start_element
                while current_element and current_element != anime_exclusive_heading:
                    if current_element.name == 'table':
                        relevant_tables.append(current_element)
                    current_element = current_element.find_next_sibling()
                    # Also check for h3 as tables can be under h3 as well (e.g., Unova)
                    if current_element and current_element.name == 'h3':
                        temp_element = current_element.find_next_sibling()
                        while temp_element and temp_element.name != 'h2' and temp_element.name != 'h3':
                            if temp_element.name == 'table':
                                relevant_tables.append(temp_element)
                            temp_element = temp_element.find_next_sibling()
                        current_element = temp_element # Move to the next h2 or h3
        else:
            relevant_tables = content_tables # If no anime exclusive, take all

        for table in relevant_tables:
            # Iterate through each row in the table (skipping the header row)
            rows = table.find_all('tr')
            if len(rows) > 1: # Ensure there's at least one data row after the header
                for row in rows[1:]: # Skip the first row (header)
                    columns = row.find_all('td')
                    if len(columns) >= 2: # Ensure there are enough columns for image and info
                        image_column = columns[0]
                        info_column = columns[1] # This column contains both name and description

                        # Extract image URL
                        img_tag = image_column.find('img', class_='mw-file-element')
                        if img_tag and 'data-src' in img_tag.attrs:
                            image_url = img_tag['data-src']
                        elif img_tag and 'src' in img_tag.attrs:
                            image_url = img_tag['src']
                        else:
                            image_url = None

                        # Make sure image_url is absolute
                        if image_url and not image_url.startswith('http'):
                            image_url = "https://pokemon.fandom.com" + image_url

                        # Extract name
                        badge_name = ""
                        name_tag = info_column.find('b')
                        if name_tag:
                            badge_name = name_tag.get_text(strip=True).replace('The ', '')
                        else:
                            # Fallback if <b> not found, try to extract from the first <span> with an ID
                            span_with_id = info_column.find('span', id=True)
                            if span_with_id:
                                badge_name = span_with_id.get_text(strip=True).replace('The ', '')
                            else:
                                badge_name = "Unnamed Badge" # Default if no clear name found

                        # Extract the full text of the info_column
                        full_info_text = info_column.get_text(separator=' ', strip=True)

                        # Now, try to isolate the description by removing the badge name and any leading "The "
                        # We also need to be careful with "Abilities:" as it marks the next section
                        description = full_info_text

                        # Remove the "The [Badge Name]" prefix
                        if badge_name and full_info_text.startswith(f"The {badge_name}"):
                            description = full_info_text.replace(f"The {badge_name}", "", 1).strip()
                        elif badge_name: # Handle cases where "The " might not be there but name is
                             description = full_info_text.replace(badge_name, "", 1).strip()

                        # Remove the "is given out at..." part from the beginning of the description.
                        # This pattern seems to consistently precede the core info you want.
                        # Then take everything up to "Abilities:"
                        if description.startswith("is given out at"):
                            # Split by "Abilities:" and take the first part
                            parts = description.split("Abilities:", 1)
                            description = parts[0].strip()
                        elif "Abilities:" in description:
                             # If "is given out at" is not there, but "Abilities" is, still trim after it.
                             parts = description.split("Abilities:", 1)
                             description = parts[0].strip()

                        # Final cleanup: remove extra spaces
                        description = ' '.join(description.split())

                        # For Paldea League, the description is simpler and should be taken as is
                        if badge_name == "Unnamed Badge": # This might need a better identifier for Paldea
                             # Re-evaluate the description for Paldea specifically
                             paldea_desc_p = soup.find('h2', id='Paldea_League').find_next_sibling('p')
                             if paldea_desc_p:
                                 description = paldea_desc_p.get_text(strip=True)
                             else:
                                 description = full_info_text # Fallback

                        badges_data.append({
                            'name': badge_name,
                            'image_url': image_url,
                            'description': description
                        })
    except requests.exceptions.RequestException as e:
        print(f"Error making request to {url}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during scraping: {e}")

    return badges_data

if __name__ == "__main__":
    gym_badges_url = "https://pokemon.fandom.com/wiki/List_of_Gym_Badges"
    all_gym_badges = scrape_gym_badges(gym_badges_url)

    if all_gym_badges:
        json_output = json.dumps(all_gym_badges, indent=4, ensure_ascii=False) # ensure_ascii=False for proper display of non-ASCII characters
        print(json_output)

        with open("pokemon_gym_badges.json", "w", encoding='utf-8') as f:
            f.write(json_output)
        print("\nGym badge data saved to pokemon_gym_badges.json")
    else:
        print("No gym badge data was scraped.")
        
        
    ribbons_page_url = "https://www.serebii.net/games/ribbons.shtml"
    all_ribbons = scrape_pokemon_ribbons(ribbons_page_url)

    if all_ribbons:
        # Convert the list of dictionaries to a JSON object
        json_output = json.dumps(all_ribbons, indent=4)
        print(json_output)

        # Optionally, save to a file
        with open("pokemon_ribbons.json", "w") as f:
            f.write(json_output)
        print("\nRibbon data saved to pokemon_ribbons.json")
    else:
        print("No ribbon data was scraped.")