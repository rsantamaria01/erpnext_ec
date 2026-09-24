import barcode
from barcode.writer import ImageWriter
from barcode.writer import SVGWriter

import base64
from io import BytesIO

def get_barcode_base64(string_code):
    """Código de barras de la clave de acceso para el RIDE.
    La ficha técnica del SRI recomienda GS1-128 / Code 128 (compacto para 49 dígitos)."""
    string_code = str(string_code or "").strip()
    if not string_code or string_code == "0":
        return None

    code128 = barcode.get_barcode_class('code128')
    barcode_instance = code128(string_code, writer=ImageWriter())

    options = {
        "write_text": False,
        "module_width": 0.25,
        "module_height": 10,
        "quiet_zone": 2,
        "background": "white",
        "foreground": "black",
    }

    buffer = BytesIO()
    barcode_instance.write(buffer, options=options)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode('utf-8')


def clave_para_barcode(doc):
    """Número de autorización si ya existe; si no, la clave de acceso (son iguales en el esquema offline)."""
    for campo in ("numeroautorizacion", "numeroAutorizacion"):
        valor = str(doc.get(campo) or "").strip()
        if valor and valor != "0":
            return valor
    return doc.get("claveAcceso")

def get_barcode_svg(string_code):
    # Generar código de barras Code 39
    code39 = barcode.get_barcode_class('code39')
    barcode_instance = code39(string_code, writer=SVGWriter(), add_checksum=False)

    # Obtener el código SVG como texto
    svg_code = barcode_instance.render()

    # Imprimir el código SVG
    #print(svg_code)
    return svg_code

def get_img_base64(file_path):
    
    
    return

