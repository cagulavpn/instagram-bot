import os
import time
import threading
from flask import Flask, request, render_template_string
from instagrapi import Client

app = Flask(__name__)

bot_status = "Oprit"
bot_logs = []
bot_thread_running = False

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🪽𝐍ïght𝐋ÿfe #CGL Control</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(rgba(15, 23, 42, 0.75), rgba(15, 23, 42, 0.85)), 
                        url('https://i.ibb.co/6R228J5/image-f19b87.jpg') no-repeat center center fixed;
            background-size: cover;
            color: #f8fafc;
            padding: 20px;
            margin: 0;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .card {
            background: rgba(30, 41, 59, 0.85);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            padding: 25px;
            border-radius: 16px;
            width: 100%;
            max-width: 500px;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.6);
            border: 1px solid rgba(56, 189, 248, 0.3);
        }
        h2 { color: #38bdf8; text-align: center; margin-top: 0; text-shadow: 0 2px 4px rgba(0,0,0,0.5); }
        label { display: block; margin-top: 15px; font-weight: bold; font-size: 14px; color: #94a3b8; }
        input, textarea {
            width: 100%;
            padding: 10px;
            margin-top: 5px;
            border-radius: 8px;
            border: 1px solid #334155;
            background: rgba(15, 23, 42, 0.8);
            color: white;
            box-sizing: border-box;
            font-size: 16px;
        }
        input:focus, textarea:focus {
            outline: none;
            border-color: #38bdf8;
            box-shadow: 0 0 8px rgba(56, 189, 248, 0.4);
        }
        button {
            width: 100%;
            margin-top: 25px;
            padding: 12px;
            background: linear-gradient(135deg, #0284c7, #0369a1);
            color: white;
            border: none
