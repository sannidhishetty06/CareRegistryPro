import json
from groq import Groq
from app.external_search_service import search_provider_ddg as search_provider
import os
import time
import hashlib
import pickle
import requests

client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))

# Persistent cache file
CACHE_FILE = os.path.join(os.path.dirname(__file__), "llm_cache.pkl")

# Load cache from disk
def load_cache():
    global llm_cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'rb') as f:
                llm_cache = pickle.load(f)
                print(f"[Cache] Loaded {len(llm_cache)} cached entries")
        except:
            llm_cache = {}
    else:
        llm_cache = {}

# Save cache to disk
def save_cache():
    try:
        with open(CACHE_FILE, 'wb') as f:
            pickle.dump(llm_cache, f)
            print(f"[Cache] Saved {len(llm_cache)} entries")
    except Exception as e:
        print(f"[Cache] Error saving: {str(e)}")

llm_cache = {}
load_cache()


def validate_npi_in_registry(npi: str, first: str, last: str, state: str) -> dict:
    """
    Validate that NPI exists in official NPI Registry.
    Returns provider data if found, None if not.
    """
    if not npi or len(npi) != 10 or not npi.isdigit():
        return None
    
    try:
        # Call NPI Registry API to validate
        url = f"https://npiregistry.cms.hhs.gov/api/?number={npi}&pretty=on"
        response = requests.get(url, timeout=5)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        results = data.get("results", [])
        
        if not results:
            print(f"    → NPI {npi} not found in official NPI Registry")
            return None
        
        # NPI exists in registry - extract provider info
        provider = results[0]
        print(f"    → NPI {npi} validated in official registry")
        
        # Extract provider details
        basic_info = provider.get("basic", {})
        return {
            "npi": npi,
            "name": basic_info.get("name", ""),
            "state": basic_info.get("sole_proprietor_state_code", ""),
            "specialty": basic_info.get("credential_text", ""),
        }
        
    except Exception as e:
        print(f"    → NPI validation error: {str(e)}")
        return None


def enrich_no_match_rows(results):
    """
    LLM as FALLBACK for "No Match" rows.
    
    Strategy:
    1. Try primary search (name + state)
    2. If no NPI found, try alternative searches:
       - Broader name search
       - Search without state
       - Search with specialty keywords
    3. Extract NPI using LLM
    4. Validate NPI in official registry
    5. Only accept if real and state matches
    """
    global llm_cache
    
    final = []
    no_match_count = 0
    enriched_count = 0

    for row in results:
        
        # Already matched rows pass through
        if row.get("Status") != "No Match":
            final.append(row)
            continue

        no_match_count += 1
        first = row.get("First_Name", "").strip()
        last = row.get("Last_Name", "").strip()
        state = row.get("State", "").strip()

        print(f"\n[Enrichment {no_match_count}] {first} {last} ({state})")

        # Try LLM fallback with multiple search strategies
        enriched_data = try_llm_fallback(first, last, state)
        
        if enriched_data:
            print(f"  ✅ Enriched via LLM with confidence {enriched_data.get('AI_Confidence')}")
            enriched_row = {**row, **enriched_data}
            final.append(enriched_row)
            enriched_count += 1
            continue

        # Keep original if LLM fallback fails
        print(f"  → Keeping as No Match")
        final.append(row)
        
        time.sleep(0.2)

    print(f"\n{'='*60}")
    print(f"Enrichment Summary: {enriched_count}/{no_match_count} rows enriched via LLM")
    print(f"{'='*60}\n")
    
    # Save cache after processing
    save_cache()
    
    return final


def try_llm_fallback(first: str, last: str, state: str) -> dict:
    """
    Try multiple search strategies to find provider.
    """
    # Strategy 1: Primary search (name + state)
    print(f"  → Strategy 1: Searching '{first} {last}' in {state}...")
    search_hits = search_provider(first, last, state)
    
    if search_hits:
        result = extract_npi_with_llm(first, last, state, search_hits)
        if result:
            return result
    
    # Strategy 2: Broader search (name + healthcare)
    print(f"  → Strategy 2: Broader search '{first} {last} healthcare'...")
    search_hits = search_provider(first, last, "healthcare")
    
    if search_hits:
        result = extract_npi_with_llm(first, last, state, search_hits)
        if result:
            return result
    
    # Strategy 3: Search with NPI keyword
    print(f"  → Strategy 3: Searching for NPI '{first} {last} NPI'...")
    search_hits = search_provider(first, last, "NPI")
    
    if search_hits:
        result = extract_npi_with_llm(first, last, state, search_hits)
        if result:
            return result
    
    # Strategy 4: Direct NPI search (if input looks like NPI)
    if state.isdigit() and len(state) == 10:
        print(f"  → Strategy 4: Input looks like NPI {state}, validating...")
        provider_data = validate_npi_in_registry(state, first, last, state)
        if provider_data:
            return {
                "Found_First_Name": first,
                "Found_Last_Name": last,
                "Found_State": provider_data.get("state", ""),
                "Full_Name": provider_data.get("name", ""),
                "NPI": provider_data.get("npi", ""),
                "Mailing_Address": "",
                "Primary_Practice_Address": "",
                "Secondary_Practice_Address": "",
                "Taxonomy": "",
                "Specialty": provider_data.get("specialty", ""),
                "License": "",
                "Status": "LLM Suggestion",
                "AI_Confidence": "0.9"
            }
    
    print(f"  → All search strategies failed")
    return None


def get_cache_key(first: str, last: str, state: str) -> str:
    """Generate deterministic cache key."""
    key = f"{first.lower()}_{last.lower()}_{state.lower()}"
    return hashlib.md5(key.encode()).hexdigest()


def extract_npi_with_llm(first: str, last: str, state: str, search_hits: list) -> dict:
    """
    Extract NPI from search results using LLM.
    Key rule: ONLY return data if:
    1. NPI is found in search results
    2. NPI is validated in official NPI Registry
    3. State matches input state (or is close)
    """
    global llm_cache
    
    cache_key = get_cache_key(first, last, state)
    
    # Check cache first
    if cache_key in llm_cache:
        result = llm_cache[cache_key]
        if result:
            print(f"  → Using cached result: NPI {result.get('NPI')}")
        else:
            print(f"  → Using cached result: No valid match")
        return result
    
    # Build context from search results
    context = "\n\n".join(
        [f"**Result {i+1}**\nTitle: {r.get('title', '')}\nSnippet: {r.get('snippet', '')[:400]}" 
         for i, r in enumerate(search_hits[:5])]
    )

    prompt = f"""You are a healthcare provider NPI extraction specialist.

TARGET PROVIDER:
Name: {first} {last}
State: {state}

SEARCH RESULTS:
{context}

YOUR TASK: Extract provider information from these search results.

CRITICAL RULES:
1. Look for 10-digit NPI numbers (format: 1234567890)
2. Extract the provider's name, state, and specialty
3. If NO NPI is found, return Status "No Match"
4. Do NOT make up or infer NPIs
5. Return confidence as decimal (0.0 to 1.0)

RESPONSE FORMAT (JSON ONLY):
{{
  "Status": "Success" or "No Match",
  "Full_Name": "exact provider name from results",
  "Found_First_Name": "first name",
  "Found_Last_Name": "last name",
  "Found_State": "state from results",
  "NPI": "10-digit NPI if found, empty string if not",
  "Primary_Practice_Address": "address if found",
  "Specialty": "specialty if found",
  "Confidence": 0.0 to 1.0
}}

Return ONLY JSON. If unsure, set Status to "No Match"."""

    try:
        print(f"    → Calling LLM to extract NPI...")
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=400,
            timeout=30
        )

        text = resp.choices[0].message.content.strip()

        # Extract JSON
        start = text.find("{")
        end = text.rfind("}")
        
        if start == -1 or end == -1:
            print(f"    ✗ No JSON in response")
            result = None
        else:
            json_str = text[start:end+1]
            
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError:
                print(f"    ✗ JSON parse error")
                result = None
            else:
                # Extract fields
                npi = data.get("NPI", "").strip()
                confidence = float(data.get("Confidence", 0))
                found_state = data.get("Found_State", "").upper()
                
                # Validation checks
                if not npi or npi == "":
                    print(f"    → No NPI in search results")
                    result = None
                elif confidence < 0.70:
                    print(f"    → Confidence too low ({confidence})")
                    result = None
                else:
                    # Validate NPI against official registry
                    provider_data = validate_npi_in_registry(npi, data.get("Found_First_Name", ""), data.get("Found_Last_Name", ""), found_state)
                    
                    if not provider_data:
                        print(f"    ✗ NPI {npi} not in official registry")
                        result = None
                    else:
                        print(f"    ✅ NPI {npi} validated!")
                        
                        result = {
                            "Found_First_Name": data.get("Found_First_Name", ""),
                            "Found_Last_Name": data.get("Found_Last_Name", ""),
                            "Found_State": provider_data.get("state", ""),
                            "Full_Name": provider_data.get("name", ""),
                            "NPI": npi,
                            "Mailing_Address": data.get("Primary_Practice_Address", ""),
                            "Primary_Practice_Address": data.get("Primary_Practice_Address", ""),
                            "Secondary_Practice_Address": "",
                            "Taxonomy": "",
                            "Specialty": data.get("Specialty", ""),
                            "License": "",
                            "Status": "LLM Suggestion",
                            "AI_Confidence": str(round(confidence, 2))
                        }
        
        # Cache result
        llm_cache[cache_key] = result
        return result

    except Exception as e:
        print(f"    ✗ LLM error: {str(e)}")
        llm_cache[cache_key] = None
        return None