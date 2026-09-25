## ERPNext Ec

Localización ecuatoriana para ERPNext v16: comprobantes electrónicos del SRI (factura, nota de crédito, nota de débito, guía de remisión, comprobante de retención y liquidación de compra), firma XAdES-BES, envío y autorización, RIDE y correo al cliente.

Fork mantenido por Raúl Santamaría (`rsantamaria01/erpnext_ec`); los cambios se hacen directamente en `main`.

### Cómo se configura

Todo está en el workspace **SRI**, que es el único del app. Al abrirlo, el bloque **Estado SRI** muestra si la compañía está lista para emitir: los puntos de emisión activos por ambiente, la firma y su vencimiento, el envío automático y las alertas.

| Dónde | Qué se configura |
|---|---|
| **Compañía → pestaña SRI** | Datos del contribuyente (nombre comercial, RIMPE, contabilidad, agente de retención, gran contribuyente, RUC proveedor), firma electrónica, herramienta de firma, timeout, modo simulación, envío automático (lote y cron), correo por defecto para clientes sin correo, y formatos/plantillas del RIDE. |
| **SRI Establecimiento** | Establecimientos registrados en el RUC (código de 3 dígitos). Se pueden **deshabilitar** en lugar de borrarlos. |
| **SRI Punto de Emisión** | Puntos de emisión de cada establecimiento, con sus secuenciales. **El punto define el ambiente del documento**: `DES` (pruebas, celcer) o `PRO` (producción). Se pueden deshabilitar. |
| **SRI Firma Electrónica** | Archivo `.p12` y su contraseña. |

#### Ambiente por punto de emisión

No hay un interruptor DEV/PRO por compañía: cada documento toma el ambiente de su punto de emisión, y con él la URL del SRI y el dígito de ambiente de la clave de acceso. Así se pueden hacer pruebas en un punto `DES` mientras se factura de verdad en uno `PRO`.

- Un punto `DES` exige **Test Dev Environment Email**. Los RIDE de ese punto se envían solo a ese correo, nunca al cliente.
- Un punto `PRO` envía al correo del cliente. Si el cliente no tiene correo, usa el **correo por defecto** de la pestaña SRI.
- Un documento ya autorizado conserva el ambiente de su número de autorización, aunque después se cambie el punto.
- En los formularios, los campos de establecimiento y punto solo muestran registros activos de la compañía y del establecimiento elegido.
- Las facturas de prueba emitidas desde un punto `DES` igual afectan la contabilidad y el inventario. Para probar el flujo completo conviene usar un sitio clonado.

#### Firma electrónica

La **herramienta de firma** de la pestaña SRI puede ser:

- `Python`: firma XAdES-BES nativa (`utilities/xades_tool_v4.py`, con `cryptography` y `lxml`). Verificada con `xmlsec1` sobre el XML que genera el app.
- `XadesSignerCmd`: binario .NET heredado del proyecto original (`utilities/apps/XadesSignerCmd`). Se retirará cuando la firma Python quede confirmada con el SRI.

#### Envío automático

Con **Envío automático al SRI** activo, una tarea programada que corre cada minuto revisa el cron configurado (por defecto `*/5 * * * *`). Cuando toca, envía las facturas y notas de crédito emitidas que aún no tienen respuesta del SRI, siempre que hayan pasado 3 minutos desde su última modificación. No corre en modo simulación.

### Instalación (bench v16)

```bash
bench get-app https://github.com/rsantamaria01/erpnext_ec
uv pip install -e ./apps/erpnext_ec --python ./env/bin/python
bench --site <sitio> install-app erpnext_ec
bench --site <sitio> migrate
bench build --app erpnext_ec   # requiere Node >= 24
```

En Frappe v16, `install-app` marca los patches como completados sin ejecutarlos, por eso hace falta correr `bench migrate` después de instalar.

### Actualización

```bash
export PATH="$HOME/.local/bin:$PATH"
cd /opt/frappe-bench/apps/erpnext_ec && git pull
cd /opt/frappe-bench
bench --site <sitio> backup
bench --site <sitio> migrate
bench build --app erpnext_ec
bench restart
```

Los patches de `patches.txt` hacen la migración de datos de forma idempotente:

- `sri_modulo_unico`: une los módulos antiguos en el módulo **SRI**.
- `sri_renombrar_doctypes`: aplica los nombres en español de los DocTypes. Los registros conservan su nombre: `PTO-00001`, `EST-00001`, …
- `sri_ambiente_por_punto`: el ambiente pasa a definirse por punto de emisión.
- `sri_config_en_compania`: la configuración de *Regional Settings Ec* pasa a la pestaña SRI de Compañía.
- `sri_workspace_unico`: crea el bloque Estado SRI.

### Compatibilidad

- **ERPNext / Frappe v16**, **Python 3.14** con **uv**.
- **Ficha Técnica SRI 2.34 (julio 2026)**:
  - Factura, nota de crédito, nota de débito, guía de remisión y liquidación de compra en XML 1.1.0.
  - Anexos 23 a 26: `codigoAuxiliar`, Gran Contribuyente, `<placa>` y RUC Proveedor.
  - RIDE con subtotal de tarifa especial.
  - Catálogos actualizados.
  - XSD de validación local.

### Licencia

MIT (ver [LICENSE](LICENSE)).
