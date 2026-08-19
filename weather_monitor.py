# ----- START COPYING FULL CODE HERE -----
import os
import time
import requests
# --- Make sure this library is updated: pip install --upgrade google-generativeai ---
import google.generativeai as genai

# --- Step 1: PASTE YOUR API KEYS HERE ---
GOOGLE_AI_API_KEY = "ulala" # <--- Replace this text
OPENWEATHERMAP_API_KEY = "ulala" # <--- Replace this text
# --------------------------------------------

# --- Configuration for Delays ---
LONG_DELAY_SECONDS = 30 * 60 # 30 minutes
SHORT_DELAY_SECONDS = 1      # Almost immediate (1 second to allow messages to print)
# --------------------------------

# Configure the Google AI Client using your key
try:
    genai.configure(api_key=GOOGLE_AI_API_KEY)
except Exception as e:
    print(f"Error configuring Google AI: {e}")
    print("Please ensure your Google AI API Key is correctly pasted above.")
    exit()

# Check if OpenWeatherMap key is placeholder
if "PASTE_YOUR_OPENWEATHERMAP_API_KEY_HERE" in OPENWEATHERMAP_API_KEY or not OPENWEATHERMAP_API_KEY:
     print("Error: OpenWeatherMap API Key is missing or still has the placeholder text.")
     print("Please paste your OpenWeatherMap key into the script.")
     exit()

# --- Define the structure of our Weather Tool (Simpler Dictionary Style) ---
get_weather_tool_dict = {
    "function_declarations": [
        {
            "name": "getCurrentWeather",
            "description": "Gets the current real-time weather for a specific location.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "location": {
                        "type": "STRING",
                        "description": "The city and state, or city and country, e.g., \"London, UK\" or \"San Francisco, CA\""
                    },
                    "units": {
                        "type": "STRING",
                        "description": "Optional. The temperature units to use. Can be \"metric\" (Celsius) or \"imperial\" (Fahrenheit). Defaults to metric if not specified."
                    }
                },
                "required": ["location"]
            }
        }
    ]
}
# --- End of Tool Definition ---


# --- Create the AI Model and tell it about our Tool ---
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash-latest",
    tools=[get_weather_tool_dict]
)

# --- This is the Python function that ACTUALLY gets the weather ---
def get_weather_from_api(location, units="metric"):
    """Calls the OpenWeatherMap API."""
    print(f"...Requesting weather for '{location}' in '{units}' units from OpenWeatherMap...")
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    safe_units = units if units in ["metric", "imperial"] else "metric"
    params = {
        'q': location,
        'appid': OPENWEATHERMAP_API_KEY,
        'units': safe_units
    }
    api_result = {}

    try:
        response = requests.get(base_url, params=params, timeout=15)
        response.raise_for_status()
        weather_data = response.json()

        main_weather = weather_data.get('weather', [{}])[0].get('description', 'N/A')
        temp = weather_data.get('main', {}).get('temp', 'N/A')
        humidity = weather_data.get('main', {}).get('humidity', 'N/A')
        wind_speed = weather_data.get('wind', {}).get('speed', 'N/A')
        city_name = weather_data.get('name', 'N/A')
        country = weather_data.get('sys', {}).get('country', '')
        feels_like_temp = weather_data.get('main', {}).get('feels_like', 'N/A')
        min_temp = weather_data.get('main', {}).get('temp_min', 'N/A')
        max_temp = weather_data.get('main', {}).get('temp_max', 'N/A')

        api_result = {
            "location_found": f"{city_name}, {country}".strip(", "),
            "temperature": temp,
            "temperature_feels_like": feels_like_temp,
            "temperature_min": min_temp,
            "temperature_max": max_temp,
            "condition": main_weather.capitalize(),
            "humidity_percent": humidity,
            "wind_speed": wind_speed,
            "units": safe_units
        }

    except requests.exceptions.Timeout:
        print("Error: OpenWeatherMap request timed out.")
        api_result = {"error": "Request to weather service timed out"}
    except requests.exceptions.HTTPError as http_err:
        status_code = http_err.response.status_code
        error_msg = f"HTTP error {status_code}"
        if status_code == 401: error_msg = "Authentication failed (check OpenWeatherMap API key)"
        elif status_code == 404: error_msg = f"City '{location}' not found by OpenWeatherMap"
        print(f"Error: {error_msg}")
        api_result = {"error": error_msg}
    except requests.exceptions.RequestException as req_err:
        error_msg = f"Network error contacting OpenWeatherMap: {req_err}"
        print(f"Error: {error_msg}")
        api_result = {"error": error_msg}
    except Exception as e:
        error_msg = f"An unexpected error occurred while getting weather: {e}"
        print(f"Error: {error_msg}")
        api_result = {"error": "An unexpected error occurred"}

    return api_result


# --- Main Part of the Script ---
print("-" * 30)
print("Weather Monitor Initialized")
print("Using Google AI + OpenWeatherMap")
print("-" * 30)

# Start a chat session with the AI model
chat = model.start_chat(enable_automatic_function_calling=False) # Manual handling

# --- Ask for the INITIAL location ---
location_to_monitor = input("Enter the initial location to monitor (e.g., London, UK): ")
if not location_to_monitor.strip():
     print("No location entered. Exiting.")
     exit()
print(f"--- Starting monitor for: {location_to_monitor} ---")
# --------------------------------

last_weather_api_result = None
# Initialize wait_seconds for the very first loop iteration (short delay)
wait_seconds = SHORT_DELAY_SECONDS

while True: # Main loop keeps script running
    # --- Wait BEFORE checking weather (except for the very first time) ---
    if wait_seconds > 0:
         print(f"\n--- Waiting {wait_seconds} seconds (Press Ctrl+C for immediate stop) ---")
         time.sleep(wait_seconds)
    # Reset wait_seconds for the next decision, default to long delay unless changed
    wait_seconds = LONG_DELAY_SECONDS

    current_location_display = location_to_monitor
    try:
        # Explicitly tell the AI which units to use (e.g., metric)
        prompt = f"Give a brief summary of the current weather conditions in {location_to_monitor}, using metric units."
        # If you prefer Fahrenheit, change it to:
        # prompt = f"Give a brief summary of the current weather conditions in {location_to_monitor}, using imperial units."

        print(f"\nAsking AI for update for {current_location_display}...")
        ai_response = chat.send_message(prompt)

        ai_summary_text = "AI summary not available."
        current_weather_api_result = None
        function_called_by_ai = False

        try:
            if ai_response.candidates and ai_response.candidates[0].content.parts:
                 part = ai_response.candidates[0].content.parts[0]
                 if hasattr(part, 'function_call') and part.function_call.name == "getCurrentWeather":
                     function_called_by_ai = True

                     args = part.function_call.args
                     location_to_check = args.get('location', location_to_monitor)
                     units_to_use = args.get('units', 'metric')

                     current_weather_api_result = get_weather_from_api(location_to_check, units_to_use)

                     if current_weather_api_result and "error" not in current_weather_api_result:
                         last_weather_api_result = current_weather_api_result
                         response_data_to_send = current_weather_api_result
                     elif current_weather_api_result and "error" in current_weather_api_result:
                          if last_weather_api_result:
                               print("Warning: Current fetch failed, using previous data for AI summary.")
                               response_data_to_send = last_weather_api_result
                          else:
                               print("Error: Initial/Current fetch failed.")
                               ai_summary_text = f"Error getting weather: {current_weather_api_result.get('error')}"
                               function_called_by_ai = False
                               raise StopIteration

                     function_response_part = genai.protos.Part(
                         function_response=genai.protos.FunctionResponse(
                             name="getCurrentWeather",
                             response=response_data_to_send
                         )
                     )
                     ai_response_after_function = chat.send_message(function_response_part)

                     if hasattr(ai_response_after_function, 'text'):
                          ai_summary_text = ai_response_after_function.text
                     else:
                          try: ai_summary_text = ai_response_after_function.candidates[0].content.parts[0].text
                          except (AttributeError, IndexError): ai_summary_text = "(Could not extract AI summary)"

                 else:
                      print("AI did not request the weather function this time.")
                      ai_summary_text = part.text
            else:
                 print("Warning: AI response structure might be empty or missing parts.")
                 ai_summary_text = "(Received empty or unexpected response from AI)"

        except StopIteration:
              pass # Handled fetch error already
        except Exception as e:
            print(f"Error processing AI response or function call: {e}")
            try: ai_summary_text = ai_response.text
            except: ai_summary_text = "Error processing AI response."


        # 6. Print the final output
        print(f"\n--- Weather Update for {current_location_display} ---")
        if not function_called_by_ai or (current_weather_api_result and "error" in current_weather_api_result):
             print(f"AI Status: {ai_summary_text}")

        if last_weather_api_result and "error" not in last_weather_api_result:
            try:
                loc_found = last_weather_api_result.get('location_found', 'N/A')
                temp = last_weather_api_result.get('temperature', 'N/A')
                feels_like = last_weather_api_result.get('temperature_feels_like', 'N/A')
                temp_min = last_weather_api_result.get('temperature_min', 'N/A')
                temp_max = last_weather_api_result.get('temperature_max', 'N/A')
                condition = last_weather_api_result.get('condition', 'N/A')
                humidity = last_weather_api_result.get('humidity_percent', 'N/A')
                wind = last_weather_api_result.get('wind_speed', 'N/A')
                units = last_weather_api_result.get('units', 'metric')
                temp_symbol = "°C" if units == 'metric' else "°F"
                wind_symbol = " m/s" if units == 'metric' else " mph"

                if function_called_by_ai and not (current_weather_api_result and "error" in current_weather_api_result):
                    print(f"Summary: {ai_summary_text}")

                print("-" * 25)
                print(f" Location:    {loc_found}")
                print(f" Condition:   {condition}")
                print(f" Temperature: {temp}{temp_symbol}")
                if feels_like != 'N/A': print(f" Feels Like:  {feels_like}{temp_symbol}")
                if temp_min != 'N/A' and temp_max != 'N/A': print(f" Day Min/Max: {temp_min}{temp_symbol} / {temp_max}{temp_symbol}")
                if humidity != 'N/A': print(f" Humidity:    {humidity}%")
                if wind != 'N/A': print(f" Wind Speed:  {wind}{wind_symbol}")
                print("-" * 25)

            except Exception as e:
                print(f"    (Could not format details: {e})")

        if current_weather_api_result and "error" in current_weather_api_result:
             print(f"\nNOTE: Latest update attempt failed - {current_weather_api_result.get('error')}")


        # --- Ask user what to do next AND set appropriate delay ---
        print("\n--- Options ---")
        next_action = input(f"Press ENTER to check '{current_location_display}' again (in 30 mins), type new city (immediate check), or 'quit': ").strip()

        if next_action.lower() == 'quit':
            print("Exiting...")
            break # Exit the main while loop

        elif next_action == "":
            # User pressed Enter, keep same city, use LONG delay
            wait_seconds = LONG_DELAY_SECONDS
            print(f"Okay, checking '{current_location_display}' again after delay.")
            pass # Continue loop

        else:
            # User entered something else, assume it's a new city
            location_to_monitor = next_action # Update the location for the NEXT loop iteration
            last_weather_api_result = None # Reset last known data for new city
            wait_seconds = SHORT_DELAY_SECONDS # Use SHORT delay for immediate check
            print(f"Okay, switching monitor to: {location_to_monitor}")
        # --- End of decision section ---


    # This except handles Ctrl+C press
    except KeyboardInterrupt:
        print("\n\nStopping monitor...")
        break # Exit the while loop

    # This except handles MOST other errors that might occur inside the loop
    except Exception as e:
        print(f"\n!!! An unexpected error occurred in the main loop: {e} !!!")
        print("--- Will try again after a short delay ---")
        time.sleep(15) # Wait a bit longer after an unexpected error

print("\nWeather monitor stopped.")
# ----- END COPYING FULL CODE HERE -----