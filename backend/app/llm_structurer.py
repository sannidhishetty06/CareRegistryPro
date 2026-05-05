from groq import Groq
import json
import os

client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))

def structure_provider_from_text(first, last, state, snippet):
    """
    Extract structured provider info from search snippet.
    Used as utility for LLM-based extraction.
    """
    prompt = f"""You are a healthcare provider data extraction specialist.

Input provider:
- Name: {first} {last}
- State: {state}

Search snippet:
{snippet}

Extract structured info. Return JSON ONLY:
{{
 "Full_Name": "",
 "Probable_Address": "",
 "Probable_Specialty": "",
 "Confidence": 0.0
}}
"""

    try:
        r = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=300
        )

        text = r.choices[0].message.content.strip()
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            return json.loads(text[start:end+1])
        return None

    except Exception as e:
        print(f"LLM structure error: {str(e)}")
        return None