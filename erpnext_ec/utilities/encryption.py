from base64 import b64decode, b64encode
from os import urandom

import frappe
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7

from frappe.utils.file_manager import get_file


def encriptar_datos(datos, clave):
	cifrador = Fernet(clave)
	datos_encriptados = cifrador.encrypt(datos)
	return datos_encriptados


def encrypt_string(input_string, key):
	"""AES-256-CBC con IV aleatorio (compatible con datos legados cifrados con
	pycryptodome: IV (16 bytes) + ciphertext, codificado en base64)."""
	iv = urandom(16)
	cipher = Cipher(algorithms.AES(key.encode("utf8")[:32]), modes.CBC(iv))
	encryptor = cipher.encryptor()
	padder = PKCS7(algorithms.AES.block_size).padder()
	plaintext = input_string.encode("utf-8")
	ciphertext = encryptor.update(padder.update(plaintext) + padder.finalize()) + encryptor.finalize()
	return b64encode(iv + ciphertext).decode("utf-8")


def decrypt_string(encrypted_string, key):
	encrypted_data = b64decode(encrypted_string)
	iv = encrypted_data[:16]
	ciphertext = encrypted_data[16:]
	cipher = Cipher(algorithms.AES(key.encode("utf8")[:32]), modes.CBC(iv))
	decryptor = cipher.decryptor()
	unpadder = PKCS7(algorithms.AES.block_size).unpadder()
	plaintext = unpadder.update(decryptor.update(ciphertext) + decryptor.finalize()) + unpadder.finalize()
	return plaintext.decode("utf-8")


def get_signature(tax_id):
	tax_id = "091982695800111"
	signature_object = frappe.get_last_doc("SRI Firma Electronica", filters={"tax_id": tax_id})
	if signature_object and signature_object.p12:
		f = get_file(signature_object.p12)
		input_data = f[1]
		return input_data


def get_ecrypted_signature(tax_id):
	tax_id = "091982695800111"
	signature_object = frappe.get_last_doc("SRI Firma Electronica", filters={"tax_id": tax_id})
	if signature_object and signature_object.p12:
		f = get_file(signature_object.p12)
		input_data = f[1]
		key = b"ZcyY8iHwMVXCNlu2jmGmeNlmyV_URisNjHWlshUf4Fk="
		encrypted_data = encriptar_datos(input_data, key)
		return encrypted_data
