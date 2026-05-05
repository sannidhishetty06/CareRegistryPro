import requests
import time

session = requests.Session()

def format_address(addr):
    """Format address from API response into readable string"""
    parts = []

    if addr.get("address_1"):
        parts.append(addr["address_1"])

    if addr.get("address_2"):
        parts.append(addr["address_2"])

    city_state_zip = " ".join(filter(None, [
        addr.get("city"),
        addr.get("state"),
        addr.get("postal_code")
    ]))

    if city_state_zip:
        parts.append(city_state_zip)

    phone = addr.get("telephone_number")
    fax = addr.get("fax_number")

    contact = []
    if phone:
        contact.append(f"Phone: {phone}")
    if fax:
        contact.append(f"Fax: {fax}")

    if contact:
        parts.append(" | ".join(contact))

    return ", ".join(parts)


def call_npi_api(row):
    """
    Call NPI Registry API with retry logic.
    Simple: first_name + last_name + state (if provided)
    """
    first_name = row.get("First_Name", "").strip()
    last_name = row.get("Last_Name", "").strip()
    state = row.get("State", "").strip() if row.get("State") else ""

    if not first_name or not last_name:
        return [{
            "First_Name": first_name,
            "Last_Name": last_name,
            "State": state,
            "Status": "Failed",
            "Error": "Missing first or last name"
        }]

    base_url = "https://npiregistry.cms.hhs.gov/api/"
    params = {
        "first_name": first_name,
        "last_name": last_name,
        "version": "2.1"
    }

    if state:
        params["state"] = state

    max_retries = 3

    for attempt in range(max_retries + 1):
        try:
            response = session.get(base_url, params=params, timeout=(3, 7))

            if response.status_code != 200:
                raise requests.exceptions.RequestException(
                    f"HTTP {response.status_code}"
                )

            try:
                data = response.json()
            except ValueError:
                raise requests.exceptions.RequestException("Invalid JSON response")

            if "Errors" in data:
                raise requests.exceptions.RequestException(f"API Error: {data['Errors']}")

            # NO MATCH
            if data.get("result_count", 0) == 0:
                return [{
                    "First_Name": first_name,
                    "Last_Name": last_name,
                    "State": state,
                    "Found_First_Name": "",
                    "Found_Last_Name": "",
                    "Found_State": "",
                    "Full_Name": "",
                    "NPI": "",
                    "Mailing_Address": "",
                    "Primary_Practice_Address": "",
                    "Secondary_Practice_Address": "",
                    "Taxonomy": "",
                    "Specialty": "",
                    "License": "",
                    "Status": "No Match"
                }]

            output_rows = []

            # SUCCESS - Process all results
            for result in data.get("results", []):

                basic = result.get("basic", {})
                addresses = result.get("addresses", [])
                practice_locations = result.get("practiceLocations", [])
                taxonomies = result.get("taxonomies", [])

                # FULL NAME
                full_name = " ".join(filter(None, [
                    basic.get("first_name"),
                    basic.get("middle_name"),
                    basic.get("last_name")
                ])).strip()

                npi_number = result.get("number", "")

                mailing_address = ""
                primary_practice = ""
                secondary_practice_list = []

                # ADDRESSES
                for addr in addresses:
                    purpose = addr.get("address_purpose", "")
                    formatted_address = format_address(addr)

                    if purpose == "MAILING":
                        mailing_address = formatted_address
                    elif purpose == "LOCATION":
                        primary_practice = formatted_address

                # PRACTICE LOCATIONS (SECONDARY)
                for pl in practice_locations:
                    formatted_secondary = format_address(pl)
                    if formatted_secondary:
                        secondary_practice_list.append(formatted_secondary)

                secondary_practice = "; ".join(secondary_practice_list)

                # STATE EXTRACTION
                found_state = ""

                # 1. Use LOCATION address
                for addr in addresses:
                    if addr.get("address_purpose") == "LOCATION" and addr.get("state"):
                        found_state = addr.get("state").upper()
                        break

                # 2. Fallback to MAILING
                if not found_state:
                    for addr in addresses:
                        if addr.get("address_purpose") == "MAILING" and addr.get("state"):
                            found_state = addr.get("state").upper()
                            break

                # 3. Fallback to input state
                if not found_state:
                    found_state = state if state else "Unknown"

                # TAXONOMY
                taxonomy_code = ""
                specialty = ""
                license_number = ""

                for tax in taxonomies:
                    primary_value = tax.get("primary")

                    if primary_value is True or str(primary_value).lower() in ["true", "y", "yes", "1"]:

                        state_value = (tax.get("state") or "").upper()
                        code_value = tax.get("code") or ""
                        desc_value = tax.get("desc") or ""
                        license_value = tax.get("license") or ""

                        if state_value and code_value:
                            taxonomy_code = f"{state_value}-{code_value}"
                        elif code_value:
                            taxonomy_code = code_value

                        if state_value and license_value:
                            license_number = f"{state_value}-{license_value}"
                        elif license_value:
                            license_number = license_value

                        specialty = desc_value
                        break

                output_rows.append({
                    "First_Name": first_name,
                    "Last_Name": last_name,
                    "State": state,
                    "Found_First_Name": basic.get("first_name", ""),
                    "Found_Last_Name": basic.get("last_name", ""),
                    "Found_State": found_state,
                    "Full_Name": full_name,
                    "NPI": npi_number,
                    "Mailing_Address": mailing_address,
                    "Primary_Practice_Address": primary_practice,
                    "Secondary_Practice_Address": secondary_practice,
                    "Taxonomy": taxonomy_code,
                    "Specialty": specialty,
                    "License": license_number,
                    "Status": "Success"
                })

            return output_rows

        except requests.exceptions.Timeout:
            if attempt < max_retries:
                time.sleep(2 ** attempt)
                continue
            else:
                return [{
                    "First_Name": first_name,
                    "Last_Name": last_name,
                    "State": state,
                    "Status": "Failed",
                    "Error": "Request timeout after retries"
                }]

        except requests.exceptions.RequestException as e:
            if attempt < max_retries:
                time.sleep(2 ** attempt)
                continue
            else:
                return [{
                    "First_Name": first_name,
                    "Last_Name": last_name,
                    "State": state,
                    "Status": "Failed",
                    "Error": str(e)
                }]

        except Exception as e:
            return [{
                "First_Name": first_name,
                "Last_Name": last_name,
                "State": state,
                "Status": "Failed",
                "Error": str(e)
            }]

    return [{
        "First_Name": first_name,
        "Last_Name": last_name,
        "State": state,
        "Status": "Failed",
        "Error": "Unexpected error"
    }]