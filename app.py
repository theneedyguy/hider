#!/usr/bin/env python3
import os
from PIL import Image
import uuid
import threading
import time
import re
###
import base64
import itertools
from typing import List, Iterator, Tuple, Union, IO
from functools import reduce
###

from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
import hashlib
import bitarray


# Initialize the Flask application
app = Flask(__name__)

# This are the paths to the upload directories
app.config['UPLOAD_FOLDER_ENC'] = './uploads_enc/'
app.config['UPLOAD_FOLDER_DEC'] = './uploads_dec/'
# These are the extension that we are accepting to be uploaded
app.config['ALLOWED_EXTENSIONS'] = set(['png', 'PNG','bmp', 'BMP'])
# We define the maximum upload size
app.config['MAX_CONTENT_LENGTH'] = 24*1024*1024

# For a given file, return whether it's an allowed type or not
def allowed_file(filename):
	return '.' in filename and \
		filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']

# This is the landing page
@app.route('/')
def index():
	return render_template('landing.html')


# Encodings (we will only use UTF-8)
ENCODINGS = {
	'UTF-8': 8,
	'UTF-32LE': 32
}






# Returns an array of bits bases on the chars we input.
# If it is less than 8 in length just prepend zeroes.
def a2bits_list(chars: str, encoding: str ='UTF-8') -> List[str]:
	return [bin(ord(x))[2:].rjust(ENCODINGS[encoding],"0") for x in chars]



# And the color with -2 and OR it with the a bit of the message.
def setlsb(color: int, bit: str) -> int:
	return color & ~1 | int(bit)


def hide(input_image: Union[str, IO[bytes]],
		message: str,
		encoding: str = 'UTF-8',
		auto_convert_rgb: bool = True):
	message_length = len(message)
	assert message_length != 0, "message length is zero"
	# Open the image
	img = Image.open(input_image)

	# Automatically convert it to RGB if not in RGBA
	if img.mode not in ['RGB', 'RGBA']:
		img = img.convert('RGB')

	encoded = img.copy()
	width, height = img.size
	index = 0

	message = str(message_length) + ":" + str(message)
	# Convert our message plus the message length + : into bits
	message_bits = "".join(a2bits_list(message, encoding))
	# If the message bit length is not divisible by 3 then append zeroes to our message.
	# This wont affect our message content since we only read the 1 bits in our reveal function.
	message_bits += '0' * ((3 - (len(message_bits) % 3)) % 3)

	npixels = width * height
	len_message_bits = len(message_bits)
	if len_message_bits > npixels * 3:
		return False
		#raise Exception("The message you want to hide is too long: {}".format(message_length))
	for row in range(height):
		for col in range(width):
			if index + 3 <= len_message_bits :

				# Get the colour component.
				pixel = img.getpixel((col, row))
				r = pixel[0]
				g = pixel[1]
				b = pixel[2]

				# Change the Least Significant Bit of each colour component.
				# Hide message bit in least significant bit of each color.
				"""
				85 is for example the color we get from the R-Value of the pixel

				85 AND -2 =
				85 = ‭0101 0101 AND -2 = (~1) = 1111 1110
					 1111 1110 RESULTS IN
				84 = ‭0101 0100‬


				'0' IS THE FIRST BIT OF THE MESSAGE
				84 OR 0 =
				84      0101 0100 OR
				0       0000 0000 =‬
						0101 0100 = 84

				Now we have hidden a '0' in the last bit of the color value R.

				"""
				r = setlsb(r, message_bits[index])
				g = setlsb(g, message_bits[index+1])
				b = setlsb(b, message_bits[index+2])

				# Save the new pixel
				if img.mode == 'RGBA':
					# Just use the default alpha pixel
					encoded.putpixel((col, row), (r, g, b, pixel[3]))
				else:
					encoded.putpixel((col, row), (r, g, b))
				# Get the next 3 bits.
				index += 3
			else:
				# Return the LSB endoded message.
				img.close()
				return encoded


def reveal(input_image: Union[str, IO[bytes]], encoding='UTF-8'):
	"""Find a message in an image (with the LSB technique).
	"""
	img = Image.open(input_image)
	width, height = img.size
	buff, count = 0, 0
	bitab = []
	limit = None
	for row in range(height):
		for col in range(width):

			# pixel = [r, g, b] or [r,g,b,a]
			pixel = img.getpixel((col, row))
			if img.mode == 'RGBA':
				pixel = pixel[:3] # ignore the alpha


			for color in pixel:
				# For each 3 color values in pixel we AND the color with 1 and shift 7 times minus the count to get from right to left :)
				"""
					84 AND 1
					84 = 0101 0100
					1  = 0000 0001 RESULTS IN
						 0000 0000 = 0

					Okay this is 0 because when we OR'd in the hiding process we or'd with a 0
					After we AND'd the original Color 85 with -2 :)

				After that we shift the number we just got 7 times - count

				0.......
				^
				We shift 0 7 times to the left wich results in 0 we append to the buffer.
				If this was a 1 then we would get 128

				"""
				buff += (color&1)<<(ENCODINGS[encoding]-1 - count)
				count += 1
				if count == ENCODINGS[encoding]:
					bitab.append(chr(buff))
					buff, count = 0, 0
					# If the last char of the message is : then the the limit by combining all the numbers before :
					if bitab[-1] == ":" and limit == None:
						try:
							limit = int("".join(bitab[:-1]))
						except:
							pass
			# if the limit is reached close the image and return the message
			if len(bitab)-len(str(limit))-1 == limit :
				img.close()
				return "".join(bitab)[len(str(limit))+1:]



def removeFile(filename):
	time.sleep(60)
	os.remove(filename)


@app.route('/enc')
def enc():
	return render_template("enc.html")

@app.route('/dec')
def dec():
	return render_template("dec.html")


# Route that will process the file upload
@app.route('/upload_enc', methods=['POST'])
def upload_enc():
	# Get the offset from the request.

	text = request.form['text']
	# Get the name of the uploaded file
	file = request.files['file']



	# Check if the file is one of the allowed types/extensions
	if file and allowed_file(file.filename):
			# Make the filename safe, remove unsupported chars
		filename = secure_filename(file.filename)
		# Move the file form the temporal folder to
		# the upload folder we setup
		file.save("./uploads_enc/"+filename)
		# Encode the file by opening it and sending it to the encoding function
		##img_to_be_encoded = Image.open()
		##encoded = encode_unlimited(img_to_be_encoded, str(text), 0)
		encoded = hide("./uploads_enc/"+filename, str(text))

		#generate random name (so we don't overwrite files)
		rndname = str(uuid.uuid4())
		try:
			fileext = str(filename).split(".")[1]
		except:
			fileext = "png"

		# If the function returns True we save the image, start the removal thread and send the user the image.
		if encoded:
			encoded.save("./uploads_enc/"+rndname+"."+fileext)
			os.remove("./uploads_enc/"+filename)
			removeThread = threading.Thread(target=removeFile , args=["./uploads_enc/"+rndname+"."+fileext])
			removeThread.start()
			return redirect(url_for('uploaded_file',filename=rndname+"."+fileext))
		else:
			###return render_template("landing.html")
			# We send the user a message that something went wrong.
			return "Message is too long!"
	# If the file is not allowed then we send feedback to the user.
	else:
		return "Unsupported file!"


# Route that will process the file upload
@app.route('/upload_dec', methods=['POST'])
def upload_dec():
	# We get the offset sent with the request.
	#offset = request.form['offset']
	#if offset == None:
	#	offset = 0
	# encryption password



	# Get the file
	file = request.files['file']
	# Check if the file is one of the allowed types/extensions
	if file and allowed_file(file.filename):
		# Make the filename safe, remove unsupported chars
		filename = secure_filename(file.filename)
		# Move the file form the temporal folder to
		# the upload folder we setup
		file.save("./uploads_dec/"+filename)
		# Encode the file
		##img_to_be_decoded = Image.open("/var/www/hider/hider/uploads_dec/"+filename)
		decoded = reveal("./uploads_dec/"+filename)
		# If the function returns True we send the message to the user.
		if decoded:
			os.remove("./uploads_dec/"+filename)
			# We replace newlines with <br/> (since we display the message as html)
			return str(decoded).replace("\n", "<br/>")
		else:
			#return render_template("landing.html")
			return "Invalid offset!"

# This route is expecting a parameter containing the name
# of a file. Then it will locate that file on the upload
# directory and show it on the browser, so if the user uploads
# an image, that image is going to be show after the upload
@app.route('/uploads_enc/<filename>')
def uploaded_file(filename):
	return send_from_directory(app.config['UPLOAD_FOLDER_ENC'],filename)


if __name__ == '__main__':
	app.run(host="0.0.0.0", port=3131)

