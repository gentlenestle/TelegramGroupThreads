from collections import defaultdict
import telethon.sync
from telethon import TelegramClient
from flask import Flask, render_template_string

app = Flask(__name__)

def group_replies_into_threads(messages):
    """
    Groups Telegram messages into threads. Messages that are not replies are treated as the starting points of threads.

    Args:
        messages (list): A list of dictionaries representing messages. Each dictionary contains:
                         - 'id': Unique identifier for the message
                         - 'text': Text content of the message
                         - 'reply_to': ID of the message this is replying to (or None if not a reply)

    Returns:
        dict: A dictionary where the keys are thread starting message IDs and values are lists of dictionaries containing message details in that thread.
    """
    threads = defaultdict(list)
    message_lookup = {msg['id']: msg for msg in messages}

    for message in messages:
        if message['reply_to'] is None:
            # This is a starting message for a thread
            threads[message['id']].append(message)
        else:
            # Find the root message for this reply
            current_id = message['reply_to']
            while current_id in message_lookup and message_lookup[current_id]['reply_to'] is not None:
                current_id = message_lookup[current_id]['reply_to']

            if current_id in message_lookup:
                # Add this message to the corresponding thread
                threads[current_id].append(message)
            else:
                # Log or handle the missing reference
                print(f"Warning: Message with ID {message['id']} references a non-existent reply_to ID {message['reply_to']}.")

    return threads

# Set up Telegram client
api_id = "yourId" #Replace with your api_id
api_hash = "yourHash" #Replace with your api_hash
client = TelegramClient('session_name', api_id, api_hash)

def fetch_group_by_name(client, group_name):
    """
    Fetch a group by its name.

    Args:
        client (TelegramClient): An instance of the Telegram client.
        group_name (str): The name of the group to fetch.

    Returns:
        Dialog: The chat object of the specified group.
    """
    for dialog in client.iter_dialogs():
        if dialog.is_group and dialog.title == group_name:
            return dialog
    raise ValueError(f"Group with name '{group_name}' not found.")

def fetch_recent_messages(client, chat, limit=1000):
    """
    Fetch recent messages from a chat.

    Args:
        client (TelegramClient): An instance of the Telegram client.
        chat (Dialog): A chat object.
        limit (int): Number of messages to fetch.

    Returns:
        list: List of message dictionaries.
    """
    messages = []
    for message in client.iter_messages(chat, limit=limit):
        messages.append({
            "id": message.id,
            "text": message.text,
            "reply_to": message.reply_to_msg_id
        })
    return messages

with client:
    group_name = "Простые Обсуждения"  # Replace with the name of the group you want to process
    group = fetch_group_by_name(client, group_name)

    group_messages = fetch_recent_messages(client, group, limit=1000)
    group_threads = group_replies_into_threads(group_messages)

    # Reverse messages in each thread
    for thread_id in group_threads:
        group_threads[thread_id].reverse()

html_template = """
<!DOCTYPE html>
<html>
<head>
    <style>
        .thread {
            margin-bottom: 20px;
        }
        .thread-title {
            font-weight: bold;
            cursor: pointer;
        }
        .thread-messages {
            display: none;
            margin-left: 20px;
        }
    </style>
    <script>
        function toggleThread(threadId) {
            const messagesDiv = document.getElementById(`thread-${threadId}`);
            if (messagesDiv.style.display === "none") {
                messagesDiv.style.display = "block";
            } else {
                messagesDiv.style.display = "none";
            }
        }
    </script>
</head>
<body>
    <h1>Group: {{ group_name }}</h1>
    {% for thread_id, messages_in_thread in group_threads.items() %}
        <div class="thread">
            <div class="thread-title" onclick="toggleThread('{{ thread_id }}')">
                💬 {{ messages_in_thread[0]['text'] or 'No Text' }}
            </div>
            <div class="thread-messages" id="thread-{{ thread_id }}">
                {% for msg in messages_in_thread %}
                    <div>➡️{{ msg['text'] or 'No Text' }}</div>
                {% endfor %}
            </div>
        </div>
    {% endfor %}
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(html_template, group_name=group_name, group_threads=group_threads)

if __name__ == '__main__':
    app.run(debug=True)
