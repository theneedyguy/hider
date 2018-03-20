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
			print(pixel)
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

hide("/Users/user/Desktop/in.png")
print(reveal("/Users/user/Desktop/out.png"))
