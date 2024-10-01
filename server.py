import logging
import requests
from requests.auth import HTTPBasicAuth
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from flask import Flask, send_file
import os  # Ensure to import os for directory handling

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Hardcoded osu! API credentials (replace with your actual credentials) (switch to env variables)
CLIENT_ID = 'Placeholder'
CLIENT_SECRET = 'Placeholder'

def get_oauth_token(client_id, client_secret):
    logging.info("Attempting to get OAuth token")
    token_url = "https://osu.ppy.sh/oauth/token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
        "scope": "public"
    }
    try:
        response = requests.post(token_url, data=data, auth=HTTPBasicAuth(client_id, client_secret))
        response.raise_for_status()
        token = response.json().get("access_token")
        logging.info("Successfully obtained OAuth token")
        return token
    except requests.RequestException as e:
        logging.error(f"Failed to get OAuth token: {str(e)}")
        return None

def get_osu_user_info(access_token, user_id):
    logging.info(f"Attempting to get user info for user ID: {user_id}")
    user_base_url = f"https://osu.ppy.sh/api/v2/users/{user_id}/fruits"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(user_base_url, headers=headers)
        response.raise_for_status()
        user_info = response.json()
        logging.info("Successfully retrieved user info")
        return user_info
    except requests.RequestException as e:
        logging.error(f"Failed to get user info: {str(e)}")
        return None

def get_rank1000_player(access_token, mode):
    logging.info(f"Attempting to get rank 1000 player for mode: {mode}")
    rank_base_url = f"https://osu.ppy.sh/api/v2/rankings/{mode}/performance"
    rank_headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    params = {
        "cursor[page]": 20,
        "limit": 50
    }
    try:
        rank = requests.get(rank_base_url, headers=rank_headers, params=params)
        rank.raise_for_status()
        rank_info = rank.json()
        logging.info("Successfully retrieved rank info")
        return rank_info
    except requests.RequestException as e:
        logging.error(f"Failed to get rank info: {str(e)}")
        return None

def draw_centered_text(draw, text, x, y, font, color):
    text_width, text_height = draw.textsize(text, font=font)
    position = (x - text_width / 2, y - text_height / 2)
    draw.text(position, text, fill=color, font=font)

def generate_image():
    logging.info("Starting image generation process")

    mode = "fruits"
    user_id = 14337744  # Replace with the desired user ID

    access_token = get_oauth_token(CLIENT_ID, CLIENT_SECRET)

    if access_token:
        user_info = get_osu_user_info(access_token, user_id)

        if user_info:
            username = user_info['username']
            user_pp = user_info['statistics']['pp']
            user_ranking = user_info['statistics']['global_rank']
            user_country_ranking = user_info['statistics']['country_rank']
            user_country = user_info['country']['code']

            rank_info = get_rank1000_player(access_token, mode)
            if rank_info and 'ranking' in rank_info:
                rankings = rank_info['ranking']
                if len(rankings) >= 50:
                    rank_1000_player = rankings[-1]

                    name = rank_1000_player['user']['username']
                    rank_pp = rank_1000_player['pp']
                    global_rank = rank_1000_player['global_rank']
                    rank_country = rank_1000_player['user']['country']['code']

                    rank_difference = (user_ranking - global_rank)
                    pp_needed = (rank_pp - user_pp)

                    try:
                        imageTemplate = Image.open("/home/Wormsniffer/mysite/bg.png").convert('RGB')
                        draw = ImageDraw.Draw(imageTemplate)

                        try:
                            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                            font_size = 20
                            font = ImageFont.truetype(font_path, font_size)
                        except IOError:
                            logging.warning("Failed to load TrueType font; using default font")
                            font = ImageFont.load_default()

                        text_color = (101, 74, 187)

                        draw_centered_text(draw, f"{username} ({user_country})", 150, 75, font, text_color)
                        draw_centered_text(draw, f"Rank: #{user_ranking}", 150, 100, font, text_color)
                        draw_centered_text(draw, f"{int(user_pp)}PP", 150, 125, font, text_color)

                        draw_centered_text(draw, "3 DIGIT WHEN??", 445, 75, font, text_color)
                        draw_centered_text(draw, f"{int(pp_needed)}PP diff", 445, 100, font, text_color)
                        draw_centered_text(draw, f"Rank Difference: {rank_difference}", 445, 125, font, text_color)

                        draw_centered_text(draw, f"Catch rank #{global_rank}", 738, 75, font, text_color)
                        draw_centered_text(draw, f"{name} ({rank_country})", 738, 100, font, text_color)
                        draw_centered_text(draw, f"{int(rank_pp)}PP", 738, 125, font, text_color)

                        output_dir = "/home/Wormsniffer/mysite"
                        os.makedirs(output_dir, exist_ok=True)
                        imageTemplate.save(os.path.join(output_dir,"stats_image.png"))

                        logging.info(f"Image saved successfully at {datetime.now().isoformat()}")
                    except Exception as e:
                        logging.error(f"Error during image creation: {str(e)}")
                else:
                    logging.error("Not enough rankings returned to find rank 1000 player")
            else:
                logging.error("Failed to retrieve rank information or 'ranking' key not found in response")
        else:
            logging.error("Failed to retrieve user info")
    else:
        logging.error("Failed to obtain access token")

@app.route('/')
def home():
    logging.info("Home route accessed")
    return "Welcome to the osu! stats generator!"

@app.route('/stats_image.png')
def serve_image():
    logging.info("Attempting to serve stats image")
    try:
        return send_file('/home/Wormsniffer/mysite/stats_image.png', mimetype='image/png')
    except Exception as e:
        logging.error(f"Failed to serve image: {str(e)}")
        return str(e), 500

@app.route('/generate')
def trigger_generate():
    logging.info("Generate route accessed")
    try:
        generate_image()
        return "Image generated successfully"
    except Exception as e:
        logging.error(f"Failed to generate image: {str(e)}")
        return str(e), 500

# Automatically generate the image when the script is run
if __name__ == "__main__":
    generate_image()
    print(f'Image updated')

# No app.run() since PythonAnywhere uses WSGI
