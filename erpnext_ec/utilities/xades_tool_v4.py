from typing import Union
import re
from datetime import datetime, timezone
import base64
import hashlib
from lxml import etree
import xml.etree.ElementTree as ET
import codecs
import random

# crypto
from cryptography.hazmat.primitives.hashes import SHA1
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography import x509
from cryptography.x509 import Name
from cryptography.x509.oid import NameOID, ObjectIdentifier
from binascii import hexlify

MAX_LINE_SIZE = 76
XML_NAMESPACES = 'xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:etsi="http://uri.etsi.org/01903/v1.3.2#"'

def random_integer() -> int:
    return random.randint(990, 999989)

def get_key_info(certificate_number: int, certificate_x509: str, modulus: str, exponent: str, issuer_name: str = "", serial_number: str = "") -> str:
    return f"""<ds:KeyInfo Id="Certificate{certificate_number}"><ds:X509Data><ds:X509Certificate>{certificate_x509}</ds:X509Certificate><ds:X509IssuerSerial><ds:X509IssuerName>{issuer_name}</ds:X509IssuerName><ds:X509SerialNumber>{serial_number}</ds:X509SerialNumber></ds:X509IssuerSerial></ds:X509Data><ds:KeyValue><ds:RSAKeyValue><ds:Modulus>{modulus}</ds:Modulus><ds:Exponent>{exponent}</ds:Exponent></ds:RSAKeyValue></ds:KeyValue></ds:KeyInfo>"""

def get_signed_properties(signature_number: int, signed_properties_number: int, certificate_x509_hash: str, X509SerialNumber: str, reference_id_number: int, issuer_name: str) -> str:
    signing_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"""<etsi:SignedProperties Id="Signature{signature_number}-SignedProperties{signed_properties_number}"><etsi:SignedSignatureProperties><etsi:SigningTime>{signing_time}</etsi:SigningTime><etsi:SigningCertificate><etsi:Cert><etsi:CertDigest><ds:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"></ds:DigestMethod><ds:DigestValue>{certificate_x509_hash}</ds:DigestValue></etsi:CertDigest><etsi:IssuerSerial><ds:X509IssuerName>{issuer_name}</ds:X509IssuerName><ds:X509SerialNumber>{X509SerialNumber}</ds:X509SerialNumber></etsi:IssuerSerial></etsi:Cert></etsi:SigningCertificate></etsi:SignedSignatureProperties><etsi:SignedDataObjectProperties><etsi:DataObjectFormat ObjectReference="#Reference-ID-{reference_id_number}"><etsi:Description>contenido comprobante</etsi:Description><etsi:MimeType>text/xml</etsi:MimeType></etsi:DataObjectFormat></etsi:SignedDataObjectProperties></etsi:SignedProperties>"""

def get_signed_info(signed_info_number: int, signed_properties_id_number: int, sha1_signed_properties: str, certificate_number: int, sha1_certificado: str, reference_id_number: int, sha1_comprobante: str, signature_number: int, signed_properties_number: int) -> str:
    return f"""<ds:SignedInfo Id="Signature-SignedInfo{signed_info_number}"><ds:CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"></ds:CanonicalizationMethod><ds:SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"></ds:SignatureMethod><ds:Reference Id="SignedPropertiesID{signed_properties_id_number}" Type="http://uri.etsi.org/01903#SignedProperties" URI="#Signature{signature_number}-SignedProperties{signed_properties_number}"><ds:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"></ds:DigestMethod><ds:DigestValue>{sha1_signed_properties}</ds:DigestValue></ds:Reference><ds:Reference URI="#Certificate{certificate_number}"><ds:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"></ds:DigestMethod><ds:DigestValue>{sha1_certificado}</ds:DigestValue></ds:Reference><ds:Reference Id="Reference-ID-{reference_id_number}" URI="#comprobante"><ds:Transforms><ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"></ds:Transform></ds:Transforms><ds:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"></ds:DigestMethod><ds:DigestValue>{sha1_comprobante}</ds:DigestValue></ds:Reference></ds:SignedInfo>"""

def get_xades_bes(xmls: str, signature_number: int, object_number: int, signed_info: str, signature: str, key_info: str, signed_properties: str) -> str:
    return f"""<ds:Signature {xmls} Id="Signature{signature_number}">{signed_info}<ds:SignatureValue Id="SignatureValue{signature_number}">{signature}</ds:SignatureValue>{key_info}<ds:Object Id="Signature{signature_number}-Object{object_number}"><etsi:QualifyingProperties Target="#Signature{signature_number}">{signed_properties}</etsi:QualifyingProperties></ds:Object></ds:Signature>"""

def sha1_base64(data: Union[str, bytes]) -> str:
    if isinstance(data, str):
        data = data.encode('utf-8')
    return base64.b64encode(hashlib.sha1(data).digest()).decode('ascii').strip()

def split_string_every_n(string: str, n: int) -> str:
    return '\n'.join(string[i:i+n] for i in range(0, len(string), n))

def canonicalize_lxml(xml_string: Union[str, bytes]) -> bytes:
    """Canonicaliza XML usando C14N sin comentarios - retorna bytes"""
    if isinstance(xml_string, bytes):
        xml_string = xml_string.decode('utf-8')
    
    root = etree.fromstring(xml_string.encode('utf-8'))
    return etree.tostring(root, method="c14n", exclusive=False, with_comments=False)

def get_modulus(n: int) -> str:
    modulus_base64 = base64.b64encode(int.to_bytes(n, (n.bit_length() + 7) // 8, 'big')).decode('latin-1')
    return '\n'.join(modulus_base64[i:i+MAX_LINE_SIZE] for i in range(0, len(modulus_base64), MAX_LINE_SIZE))

def get_exponent(e: int) -> str:
    return base64.b64encode(int.to_bytes(e, (e.bit_length() + 7) // 8, 'big')).decode().strip()

def get_x509_certificate(pem: str) -> str:
    match = re.search(r"-----BEGIN CERTIFICATE-----(.*?)-----END CERTIFICATE-----", pem, re.DOTALL)
    if match:
        clean = match.group(1).strip().replace('\n', '')
        return '\n'.join(clean[i:i+MAX_LINE_SIZE] for i in range(0, len(clean), MAX_LINE_SIZE))
    return ''

def parse_issuer_name(issuer: Name) -> str:
    """
    Parsea el issuer name en formato RFC 4514 con codificación DER hexadecimal 
    correcta para el OID 2.5.4.97 (organizationIdentifier) según estándar XAdES del SRI
    """
    # Obtener el string RFC 4514 base
    base_dn = issuer.rfc4514_string()
    
    # Buscar el atributo 2.5.4.97 (organizationIdentifier)
    oid = ObjectIdentifier("2.5.4.97")
    
    for rdn in issuer.rdns:
        for attr in rdn:
            if attr.oid == oid:
                val = attr.value
                
                # Codificar el valor según DER (Distinguished Encoding Rules)
                val_bytes = val.encode('utf-8')
                hex_val = hexlify(val_bytes).decode('ascii').upper()
                
                # Formato DER completo:
                # Tag (13 = PrintableString) + Longitud + Contenido
                # El SRI espera específicamente este formato
                tag = "13"  # 0x13 = PrintableString en ASN.1/DER
                length_hex = format(len(val_bytes), '02X')
                der_encoded = f"2.5.4.97=#{tag}{length_hex}{hex_val}"
                
                # Intentar reemplazar en diferentes formatos
                # Primero con valor escapado (para caracteres especiales)
                escaped_val = val.replace(",", "\\,").replace("+", "\\+").replace("=", "\\=").replace("#", "\\#")
                search_pattern = f"2.5.4.97={escaped_val}"
                
                if search_pattern in base_dn:
                    return base_dn.replace(search_pattern, der_encoded)
                
                # Intentar sin escapar
                search_pattern = f"2.5.4.97={val}"
                if search_pattern in base_dn:
                    return base_dn.replace(search_pattern, der_encoded)
                
                # Si no se encuentra en el DN, agregarlo al principio
                # (mantener el orden correcto según RFC 4514)
                return der_encoded + "," + base_dn
    
    return base_dn

DS_NS = "http://www.w3.org/2000/09/xmldsig#"
ETSI_NS = "http://uri.etsi.org/01903/v1.3.2#"


def _c14n(element) -> bytes:
    """C14N 1.0 inclusiva (sin comentarios) del elemento EN SU CONTEXTO: incluye
    los namespaces heredados de los ancestros, igual que lo hará el SRI al validar."""
    return etree.tostring(element, method="c14n", exclusive=False, with_comments=False)


def sign_xml(p12_data: bytes, password: bytes, xml: Union[str, bytes]) -> str:
    """
    Firma un comprobante XML con XAdES-BES (enveloped) compatible con el SRI de Ecuador.

    Los digests de SignedProperties, KeyInfo y SignedInfo se calculan sobre los
    nodos ya insertados en el documento, de modo que la canonicalización incluye
    los namespaces declarados en la raíz del comprobante (p. ej. xmlns y xmlns:ds).
    """
    # Cargar certificado y llave privada
    private_key, cert, _ = pkcs12.load_key_and_certificates(p12_data, password)

    # Información del certificado
    pem = cert.public_bytes(serialization.Encoding.PEM).decode()
    certificate_x509 = get_x509_certificate(pem)
    certificate_x509_hash = sha1_base64(cert.public_bytes(serialization.Encoding.DER))

    public_nums = cert.public_key().public_numbers()
    modulus = get_modulus(public_nums.n)
    exponent = get_exponent(public_nums.e)
    serial = cert.serial_number
    issuer_name = parse_issuer_name(cert.issuer)

    # Documento: se conserva tal cual (espacios incluidos); solo se quita la
    # declaración XML para poder re-serializar con la nuestra.
    if isinstance(xml, str):
        xml_bytes = xml.encode("utf-8")
    else:
        xml_bytes = xml
    parser = etree.XMLParser(remove_blank_text=False, resolve_entities=False)
    root = etree.fromstring(xml_bytes, parser)

    if root.get("id") != "comprobante":
        raise ValueError("El comprobante debe tener id=\"comprobante\" en el elemento raíz.")

    # 0. Digest del comprobante (transformación enveloped-signature: sin la firma)
    sha1_invoice = sha1_base64(_c14n(root))

    # IDs aleatorios
    cert_num = random_integer()
    sig_num = random_integer()
    prop_num = random_integer()
    info_num = random_integer()
    prop_id = random_integer()
    ref_id = random_integer()
    obj_num = random_integer()

    # 1. Estructura completa con digests y firma provisionales
    signed_props = get_signed_properties(sig_num, prop_num, certificate_x509_hash, serial, ref_id, issuer_name)
    key_info = get_key_info(cert_num, certificate_x509, modulus, exponent, issuer_name, str(serial))
    signed_info = get_signed_info(info_num, prop_id, "PENDIENTE", cert_num, "PENDIENTE", ref_id,
                                  sha1_invoice, sig_num, prop_num)
    xades = get_xades_bes(XML_NAMESPACES, sig_num, obj_num, signed_info, "PENDIENTE", key_info, signed_props)

    signature_el = etree.fromstring(xades.encode("utf-8"), parser)
    root.append(signature_el)

    ns = {"ds": DS_NS, "etsi": ETSI_NS}
    signed_props_el = signature_el.find(".//etsi:SignedProperties", ns)
    key_info_el = signature_el.find("ds:KeyInfo", ns)
    signed_info_el = signature_el.find("ds:SignedInfo", ns)
    refs = signed_info_el.findall("ds:Reference", ns)

    # 2. Digests de SignedProperties y KeyInfo, canonicalizados dentro del documento
    refs[0].find("ds:DigestValue", ns).text = sha1_base64(_c14n(signed_props_el))
    refs[1].find("ds:DigestValue", ns).text = sha1_base64(_c14n(key_info_el))

    # 3. Firma RSA-SHA1 del SignedInfo canonicalizado en contexto
    sig_bytes = private_key.sign(_c14n(signed_info_el), padding.PKCS1v15(), SHA1())
    signature_el.find("ds:SignatureValue", ns).text = split_string_every_n(
        base64.b64encode(sig_bytes).decode("ascii"), MAX_LINE_SIZE)

    return '<?xml version="1.0" encoding="UTF-8"?>\n' + etree.tostring(root, encoding="unicode")


def verificar_firma(signed_xml: Union[str, bytes]) -> dict:
    """Verifica una firma XAdES-BES producida por sign_xml: los tres digests
    (comprobante, SignedProperties, KeyInfo) y la firma RSA del SignedInfo con el
    certificado incluido. Es la misma validación criptográfica que hace el SRI
    (sin la cadena de confianza de la entidad certificadora)."""
    import copy
    if isinstance(signed_xml, str):
        signed_xml = signed_xml.encode("utf-8")
    root = etree.fromstring(signed_xml, etree.XMLParser(remove_blank_text=False, resolve_entities=False))
    ns = {"ds": DS_NS, "etsi": ETSI_NS}
    firma = root.find("ds:Signature", ns)
    if firma is None:
        return {"ok": False, "detalle": "El XML no tiene ds:Signature"}

    por_id = {el.get("Id"): el for el in root.iter() if el.get("Id")}
    resultados = []
    for ref in firma.find("ds:SignedInfo", ns).findall("ds:Reference", ns):
        uri = ref.get("URI", "")
        esperado = ref.find("ds:DigestValue", ns).text.strip()
        if uri == "#comprobante":
            copia = copy.deepcopy(root)
            copia.remove(copia.find("ds:Signature", ns))
            calculado = sha1_base64(_c14n(copia))
        else:
            calculado = sha1_base64(_c14n(por_id[uri[1:]]))
        resultados.append((uri, calculado == esperado))

    cert_b64 = "".join(firma.find(".//ds:X509Certificate", ns).text.split())
    cert = x509.load_der_x509_certificate(base64.b64decode(cert_b64))
    sig = base64.b64decode("".join(firma.find("ds:SignatureValue", ns).text.split()))
    try:
        cert.public_key().verify(sig, _c14n(firma.find("ds:SignedInfo", ns)), padding.PKCS1v15(), SHA1())
        rsa_ok = True
    except Exception:
        rsa_ok = False

    ok = rsa_ok and all(r[1] for r in resultados)
    return {
        "ok": ok,
        "referencias": [{"uri": u, "ok": v} for u, v in resultados],
        "firma_rsa": rsa_ok,
        "certificado": cert.subject.rfc4514_string(),
        "vence": cert.not_valid_after_utc.strftime("%Y-%m-%d %H:%M:%S"),
    }


# Integración con ERPNext
import frappe
from frappe.utils.password import get_decrypted_password

class XadesToolV4:
    def sign_xml(self, xml_string_data, doc, signature_doc):
        password_p12 = get_decrypted_password('SRI Firma Electronica', signature_doc.name, "password")
        full_path_p12 = frappe.get_site_path() + signature_doc.p12

        with open(full_path_p12, "rb") as f:
            p12_data = f.read()

        return sign_xml(p12_data, password_p12.encode(), xml_string_data)
