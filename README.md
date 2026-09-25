## ERPNext Ec

Localización ecuatoriana para ERPNext v16: comprobantes electrónicos del SRI (factura, nota de crédito, nota de débito, guía de remisión, comprobante de retención y liquidación de compra), firma XAdES-BES, envío y autorización, RIDE y correo al cliente.

Fork mantenido por Raúl Santamaría (`rsantamaria01/erpnext_ec`); los cambios se hacen directamente en `main`.

### Cómo se configura

Todo está en el workspace **SRI**, que es el único del app. Al abrirlo, el bloque **Estado SRI** muestra si la compañía está lista para emitir: los puntos de emisión activos por ambiente, la firma y su vencimiento, el envío automático y las alertas.

| Dónde | Qué se configura |
|---|---|
| **Compañía → pestaña SRI** | Datos del contribuyente (nombre comercial, RIMPE, contabilidad, agente de retención, gran contribuyente, RUC proveedor), firma electrónica, timeout, modo simulación, envío automático (lote y cron), correo por defecto para clientes sin correo, y formatos/plantillas del RIDE. |
| **Establecimientos en el RUC** (pestaña SRI) | Cuántos establecimientos abiertos tiene el RUC según el certificado del SRI. Al guardar, el app mantiene los establecimientos 001..N y, en cada uno, dos puntos de emisión por defecto: **999 (DES, pruebas)** y **001 (PRO, producción)**. Nunca se crean establecimientos fuera del RUC: lo que sobra se **borra**, y solo si ya tiene documentos se deshabilita (se borrará al sincronizar cuando ya no los tenga). El botón *Sincronizar con el RUC* de la lista de establecimientos hace lo mismo. |
| **SRI Punto de Emisión** | Secuenciales de cada punto. **El punto define el ambiente del documento**: `DES` (pruebas, celcer) o `PRO` (producción). Se pueden agregar más puntos PRO a mano (002, 003…). El SRI no acepta el punto 000. Un punto deshabilitado no numera documentos nuevos, pero sus documentos anteriores se pueden reimprimir y reenviar. |
| **SRI Firma Electrónica** | Archivo `.p12` y su contraseña. |

#### Ambiente por punto de emisión

No hay un interruptor DEV/PRO por compañía: cada documento toma el ambiente de su punto de emisión, y con él la URL del SRI y el dígito de ambiente de la clave de acceso. Así se pueden hacer pruebas en un punto `DES` mientras se factura de verdad en uno `PRO`.

- Un punto `DES` exige **Test Dev Environment Email**. Los RIDE de ese punto se envían solo a ese correo, nunca al cliente.
- Un punto `PRO` envía al correo del cliente. Si el cliente no tiene correo, usa el **correo por defecto** de la pestaña SRI.
- Un documento ya autorizado conserva el ambiente de su número de autorización, aunque después se cambie el punto.
- En los formularios, los campos de establecimiento y punto solo muestran registros activos de la compañía y del establecimiento elegido.
- Las facturas de prueba emitidas desde un punto `DES` igual afectan la contabilidad y el inventario. Para probar el flujo completo conviene usar un sitio clonado.

#### Firma electrónica

La firma es XAdES-BES con el firmador Python del app (`utilities/xades_tool_v4.py`, que usa `cryptography` y `lxml`). No depende de binarios externos.

El botón **Probar Firma** de *SRI Firma Electrónica* firma un comprobante de ejemplo con el certificado y verifica la firma sin enviar nada al SRI. Revisa los tres digests y la firma RSA, y muestra el certificado y su fecha de vencimiento.

#### Envío automático

Con **Envío automático al SRI** activo, la tarea programada revisa el cron configurado (por defecto `*/5 * * * *`). En la primera corrida del scheduler después de cada instante del cron, envía las facturas y notas de crédito emitidas que aún no tienen respuesta del SRI, siempre que hayan pasado 3 minutos desde su última modificación. No corre en modo simulación.

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
