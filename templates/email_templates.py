"""Email template generation for various notifications."""

from typing import Any, Dict


class EmailTemplate:
    """Base class for email templates."""

    def __init__(self, data: Dict[str, Any]):
        self.data = data

    def render_subject(self) -> str:
        """Render email subject."""
        raise NotImplementedError

    def render_body_text(self) -> str:
        """Render plain text email body."""
        raise NotImplementedError

    def render_body_html(self) -> str:
        """Render HTML email body."""
        raise NotImplementedError


class InvoiceEmailTemplate(EmailTemplate):
    """Email template for invoices."""

    def render_subject(self) -> str:
        invoice_number = self.data.get("invoice_number", "")
        return f"Invoice #{invoice_number}" if invoice_number else "Invoice"

    def render_body_text(self) -> str:
        customer_name = self.data.get("customer_name", "Valued Customer")
        invoice_number = self.data.get("invoice_number", "")
        invoice_date = self.data.get("invoice_date", "")
        due_date = self.data.get("due_date", "")
        total_amount = self.data.get("total_amount", 0.0)
        line_items = self.data.get("line_items", [])

        lines = [
            f"Dear {customer_name},",
            "",
            (
                f"Please find Invoice #{invoice_number} for the services provided."
                if invoice_number
                else "Please find your invoice for the services provided."
            ),
            "",
            "Invoice Details:",
            "-----------------",
            f"Invoice Number: {invoice_number}" if invoice_number else "",
            f"Invoice Date: {invoice_date}" if invoice_date else "",
            f"Due Date: {due_date}" if due_date else "",
            f"Total Amount: ${total_amount:,.2f}",
        ]

        if line_items:
            lines.append("")
            lines.append("Line Items:")
            for item in line_items:
                description = item.get("description", "")
                amount = item.get("amount", 0.0)
                lines.append(f"- {description}: ${amount:,.2f}")

        lines.extend(
            [
                "",
                "Please remit payment by the due date to avoid late fees.",
                "If you have any questions regarding this invoice, please don't hesitate to contact us.",
                "",
                "Thank you for your business!",
                "",
                "Best regards,",
                "Billing Department",
            ]
        )

        # Filter out any empty lines created by missing optional fields
        return "\n".join(line for line in lines if line != "")

    def render_body_html(self) -> str:
        customer_name = self.data.get("customer_name", "Valued Customer")
        invoice_number = self.data.get("invoice_number", "")
        invoice_date = self.data.get("invoice_date", "")
        due_date = self.data.get("due_date", "")
        total_amount = self.data.get("total_amount", 0.0)
        line_items = self.data.get("line_items", [])

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #007bff; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .invoice-details {{ background-color: white; padding: 15px; margin: 15px 0; border-radius: 5px; }}
        .line-items {{ background-color: white; padding: 15px; margin: 15px 0; border-radius: 5px; }}
        .line-item {{ padding: 8px 0; border-bottom: 1px solid #eee; }}
        .total {{ font-size: 1.2em; font-weight: bold; margin-top: 15px; padding-top: 15px; border-top: 2px solid #007bff; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Invoice #{invoice_number}</h1>
        </div>
        
        <div class="content">
            <p>Dear {customer_name},</p>
            
            <p>Please find your invoice for the services provided.</p>
            
            <div class="invoice-details">
                <h3>Invoice Details</h3>
                <p><strong>Invoice Number:</strong> {invoice_number}</p>
                <p><strong>Invoice Date:</strong> {invoice_date}</p>
                <p><strong>Due Date:</strong> {due_date}</p>
                <p class="total"><strong>Total Amount:</strong> ${total_amount:,.2f}</p>
            </div>
"""

        if line_items:
            html += """
            <div class="line-items">
                <h3>Line Items</h3>
"""
            for item in line_items:
                description = item.get("description", "")
                amount = item.get("amount", 0.0)
                html += f"""
                <div class="line-item">
                    <strong>{description}</strong>
                    <span style="float: right;">${amount:,.2f}</span>
                </div>
"""
            html += """
            </div>
"""

        html += """
            <div class="invoice-details">
                <h3>Payment Instructions</h3>
                <p>Please remit payment by the due date to avoid late fees.</p>
                <p>Payment can be made via check, ACH, or credit card.</p>
            </div>
            
            <p>If you have any questions regarding this invoice, please don't hesitate to contact us.</p>
            
            <p>Thank you for your business!</p>
        </div>
        
        <div class="footer">
            <p>Best regards,<br>Billing Department</p>
        </div>
    </div>
</body>
</html>
"""

        return html


class ContainerAlertEmailTemplate(EmailTemplate):
    """Email template for container alerts."""

    def render_subject(self) -> str:
        container_number = self.data.get("container_number", "Unknown")
        alert_type = self.data.get("alert_type", "Alert")
        return f"Container Alert: {container_number} - {alert_type}"

    def render_body_text(self) -> str:
        container_number = self.data.get("container_number", "")
        alert_type = self.data.get("alert_type", "")
        message = self.data.get("message", "")
        load_number = self.data.get("load_number", "")
        customer_name = self.data.get("customer_name", "")
        last_free_day = self.data.get("last_free_day", "")
        estimated_charges = self.data.get("estimated_charges", 0.0)

        lines = [
            "CONTAINER ALERT",
            "",
            f"Alert Type: {alert_type}",
            f"Container: {container_number}",
            f"Load: {load_number}",
            f"Customer: {customer_name}",
            "",
            message,
            "",
        ]

        if last_free_day:
            lines.append(f"Last Free Day: {last_free_day}")

        if estimated_charges > 0:
            lines.append(f"Estimated Daily Charges: ${estimated_charges:,.2f}")

        lines.extend(
            [
                "",
                "ACTION REQUIRED:",
                "Please ensure the container is returned by the last free day to avoid additional charges.",
                "",
                "For questions or concerns, please contact dispatch immediately.",
                "",
                "This is an automated alert from the Billing Agent system.",
            ]
        )

        return "\n".join(lines)

    def render_body_html(self) -> str:
        container_number = self.data.get("container_number", "")
        alert_type = self.data.get("alert_type", "")
        message = self.data.get("message", "")
        load_number = self.data.get("load_number", "")
        customer_name = self.data.get("customer_name", "")
        last_free_day = self.data.get("last_free_day", "")
        estimated_charges = self.data.get("estimated_charges", 0.0)
        urgency = self.data.get("urgency", "normal")

        alert_color = {
            "low": "#28a745",
            "normal": "#ffc107",
            "high": "#fd7e14",
            "critical": "#dc3545",
        }.get(urgency, "#ffc107")

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: {alert_color}; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .alert-box {{ background-color: white; padding: 15px; margin: 15px 0; border-left: 4px solid {alert_color}; }}
        .detail {{ padding: 8px 0; }}
        .action-box {{ background-color: #fff3cd; border: 1px solid #ffc107; padding: 15px; margin: 15px 0; border-radius: 5px; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>CONTAINER ALERT</h1>
            <h2>{alert_type}</h2>
        </div>
        
        <div class="content">
            <div class="alert-box">
                <h3>Alert Details</h3>
                <div class="detail"><strong>Container:</strong> {container_number}</div>
                <div class="detail"><strong>Load:</strong> {load_number}</div>
                <div class="detail"><strong>Customer:</strong> {customer_name}</div>
"""

        if last_free_day:
            html += f'                <div class="detail"><strong>Last Free Day:</strong> {last_free_day}</div>\n'

        if estimated_charges > 0:
            html += f'                <div class="detail"><strong>Estimated Daily Charges:</strong> ${estimated_charges:,.2f}</div>\n'

        html += f"""
                <p style="margin-top: 15px; font-size: 1.1em;">{message}</p>
            </div>
            
            <div class="action-box">
                <h3>ACTION REQUIRED</h3>
                <p>Please ensure the container is returned by the last free day to avoid additional charges.</p>
                <p>For questions or concerns, please contact dispatch immediately.</p>
            </div>
        </div>
        
        <div class="footer">
            <p>This is an automated alert from the Billing Agent system.</p>
        </div>
    </div>
</body>
</html>
"""

        return html


class DisputeResponseEmailTemplate(EmailTemplate):
    """Email template for dispute responses."""

    def render_subject(self) -> str:
        invoice_number = self.data.get("invoice_number", "")
        return (
            f"Invoice Dispute Response - Invoice #{invoice_number}"
            if invoice_number
            else "Invoice Dispute Response"
        )

    def render_body_text(self) -> str:
        customer_name = self.data.get("customer_name", "Valued Customer")
        invoice_number = self.data.get("invoice_number", "")
        response_message = self.data.get("response_message", "")
        resolution = self.data.get("resolution", "")

        lines = [
            f"Dear {customer_name},",
            "",
            f"Thank you for reaching out regarding Invoice #{invoice_number}."
            if invoice_number
            else "Thank you for reaching out regarding your invoice.",
            "",
            response_message,
            "",
            "Resolution:",
            "-----------",
            resolution,
            "",
            "If you need any additional information or documentation, please let us know and we'll be happy to provide it.",
            "",
            "We appreciate your business and look forward to resolving this matter promptly.",
            "",
            "Best regards,",
            "Billing Department",
        ]

        return "\n".join(lines)

    def render_body_html(self) -> str:
        customer_name = self.data.get("customer_name", "Valued Customer")
        invoice_number = self.data.get("invoice_number", "")
        response_message = self.data.get("response_message", "")
        resolution = self.data.get("resolution", "")

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #17a2b8; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .message-box {{ background-color: white; padding: 15px; margin: 15px 0; border-radius: 5px; }}
        .resolution-box {{ background-color: #d4edda; border: 1px solid #c3e6cb; padding: 15px; margin: 15px 0; border-radius: 5px; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Invoice Dispute Response</h1>
            <h2>Invoice #{invoice_number}</h2>
        </div>
        
        <div class="content">
            <p>Dear {customer_name},</p>
            
            <p>Thank you for reaching out regarding Invoice #{invoice_number}.</p>
            
            <div class="message-box">
                <p>{response_message}</p>
            </div>
            
            <div class="resolution-box">
                <h3>Resolution</h3>
                <p>{resolution}</p>
            </div>
            
            <p>If you need any additional information or documentation, please let us know and we'll be happy to provide it.</p>
            
            <p>We appreciate your business and look forward to resolving this matter promptly.</p>
        </div>
        
        <div class="footer">
            <p>Best regards,<br>Billing Department</p>
        </div>
    </div>
</body>
</html>
"""

        return html


def get_email_template(template_type: str, data: Dict[str, Any]) -> EmailTemplate:
    """
    Get email template by type.

    Args:
        template_type: Type of template (invoice, alert, dispute)
        data: Template data dictionary

    Returns:
        EmailTemplate instance

    Raises:
        ValueError: If template type is unknown
    """

    templates = {
        "invoice": InvoiceEmailTemplate,
        "alert": ContainerAlertEmailTemplate,
        "dispute": DisputeResponseEmailTemplate,
    }

    template_class = templates.get(template_type.lower())

    if not template_class:
        raise ValueError(f"Unknown template type: {template_type}")

    return template_class(data)

