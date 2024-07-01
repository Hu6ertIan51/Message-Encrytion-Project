from flask import Flask, request, render_template
from cryptography.fernet import Fernet
from flask_sqlalchemy import SQLAlchemy
from twilio.rest import Client

app = Flask(__name__)

# Configure the SQLAlchemy part of the app instance
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/cryptography'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Create the SQLAlchemy db instance
db = SQLAlchemy(app)

# Twilio credentials
account_sid = 'AC6a9931805ee582145c34afc0cbe46d97'
auth_token = 'cbb7a01e42ee1361548e37c8891108aa'
twilio_phone_number = '+16509104497'

client = Client(account_sid, auth_token)

# Define a model for storing messages
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    encrypted_message = db.Column(db.String(500))
    encryption_key = db.Column(db.String(44))  # Fernet keys are 32 bytes (base64 encoded is 44 characters)

@app.route('/')
def index():
    return render_template('form.html')

@app.route('/send', methods=['POST'])
def send():
    try:
        message = request.form['message']
    except KeyError:
        return 'Error: Message not found in form data.', 400  # Return a meaningful error response if 'message' is missing

    # Generate a key for encryption
    key = Fernet.generate_key()
    cipher_suite = Fernet(key)

    # Encrypt the message
    encrypted_message = cipher_suite.encrypt(message.encode()).decode()

    # Store the original message, encrypted message, and key in the database
    new_message = Message(encrypted_message=encrypted_message, encryption_key=key.decode())
    db.session.add(new_message)
    db.session.commit()

    return 'Message sent and stored!'

# Route to decrypt message and send via Twilio
@app.route('/decrypt-send', methods=['GET'])
def decrypt_send():
    # Get the latest encrypted message from database
    latest_message = Message.query.order_by(Message.id.desc()).first()

    if latest_message:
        encrypted_message = latest_message.encrypted_message
        encryption_key = latest_message.encryption_key.encode()  # Encoding key for Fernet

        # Decrypt the message
        cipher_suite = Fernet(encryption_key)
        decrypted_message = cipher_suite.decrypt(encrypted_message.encode()).decode()

        try:
            # Send decrypted message via Twilio SMS
            message = client.messages.create(
                to='+254748444576',  # Replace with your phone number
                from_=twilio_phone_number,
                body=f'Decrypted Message: {decrypted_message}'
            )
            app.logger.info(f"Message sent successfully. SID: {message.sid}")
            return 'Decrypted message sent via Twilio!'
        except Exception as e:
            app.logger.error(f"Error sending message via Twilio: {str(e)}")
            return f'Error sending message via Twilio: {str(e)}', 500
    else:
        return 'No messages found in the database.'

if __name__ == '__main__':
    with app.app_context():
        db.drop_all()
        db.create_all()  # Create database tables
    app.run(debug=True)
