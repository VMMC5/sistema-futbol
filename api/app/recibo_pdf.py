"""Genera el PDF del comprobante de pago (recibo simple)."""
from fpdf import FPDF
from fpdf.enums import XPos, YPos

from app import models


def _latin1(texto) -> str:
    return str(texto).encode("latin-1", "replace").decode("latin-1")


def generar(pago: models.Pago) -> bytes:
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 12, "Comprobante de Pago", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 8, "Sistema Integral de Canchas y Torneos", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.ln(6)

    def fila(etiqueta, valor):
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(45, 9, f"{etiqueta}:")
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 9, _latin1(valor), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    fila("Folio", pago.referencia or "-")
    fila("Concepto", pago.concepto or "-")
    fila("Titular", pago.usuario_nombre or "-")
    fila("Monto", f"$ {pago.monto:.2f}")
    fila("Método", pago.metodo)
    fila("Estado", pago.estado)
    fecha = pago.completado_en or pago.creado_en
    fila("Fecha", fecha.strftime("%Y-%m-%d %H:%M") if fecha else "-")

    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(0, 6, "Comprobante generado por el sistema. Pago simulado con fines "
                         "de demostración.")

    return bytes(pdf.output())
