# Entrega local de reportes

## Purpose

Permitir al usuario descargar localmente un PDF o Excel generado por la
aplicación. La descarga no modifica el reporte. No se envían reportes por
correo ni a servicios o destinatarios externos.

## Required inputs

- Archivo PDF o Excel generado y validado.
- Nombre, formato y advertencias del reporte.
- Estado real de verificación.

## Procedure

1. Comprobar que el archivo generado puede abrirse.
2. Preservar todas las advertencias y el estado del reporte.
3. Presentar un botón de descarga local en la interfaz.
4. No afirmar que la descarga se completó solo porque se preparó el botón.

Los borradores sin verificación deben identificarse como tales.

## Forbidden behavior

No enviar reportes a terceros ni presentar un borrador como verificado.
