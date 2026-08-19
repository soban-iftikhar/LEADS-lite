"""
Placeholder WhatsApp template config.

There's no approved Meta template yet, so this is what a real one will
look like once your supervisor issues API access. Once you have an
approved template, just update TEMPLATE_NAME / LANGUAGE_CODE and the
variable list here — nothing else in the codebase needs to change.

A WhatsApp template is approved server-side by Meta (name + language +
placeholder count are fixed), so BODY_PREVIEW below is only used for
showing a human-readable preview in the "Launch Campaign" screen — the
actual send only ever transmits the template *name* + variable values,
never raw text.
"""

TEMPLATE_NAME = "leads_outreach_intro"
LANGUAGE_CODE = "en"

# One {{1}}-style placeholder per entry, in order. Meta templates use
# positional variables (1-indexed) inside an approved body string —
# this preview just shows what that body looks like with real values
# filled in, for the Launch screen.
BODY_PREVIEW = (
    "Hi {seller_name}, this is Soban from COMSATS — I came across your "
    "property listing and wanted to reach out about a potential deal. "
    "Would you be open to a quick call this week?"
)


def build_components(seller_name: str) -> list:
    """
    Builds the `components` array for the WhatsApp Cloud API template
    message payload. Meta only accepts the variables an approved
    template actually declares — this template has one body variable
    (the seller's name).
    """
    return [
        {
            "type": "body",
            "parameters": [
                {"type": "text", "text": seller_name or "there"},
            ],
        }
    ]


def render_preview(seller_name: str) -> str:
    return BODY_PREVIEW.format(seller_name=seller_name or "there")
