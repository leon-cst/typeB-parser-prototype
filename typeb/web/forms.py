"""
WTForms definitions for the agreement-table CRUD GUI.

Validation here is deliberately permissive on Response_Format_Option
and Allowed_Dates until Parka confirms the valid value sets -- see
typeb/db/models.py for the same caveat on those two columns.
"""
import re

from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField
from wtforms.validators import DataRequired, Length, Optional, Regexp

# Loosely validates a comma-separated list of 3-letter IATA city/airport
# codes, e.g. "CGK,SIN" or "CGK, SIN, DPS". Tighten once Parka confirms
# the exact expected format for Allowed_Routes.
_ROUTE_LIST_PATTERN = re.compile(r"^\s*[A-Za-z]{3}\s*(,\s*[A-Za-z]{3}\s*)*$")


class AgreementForm(FlaskForm):
    Partner_Code = StringField(
        "Partner Code",
        validators=[DataRequired(), Length(max=10)],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    Response_Format_Option = StringField(
        "Response Format Option",
        validators=[Optional(), Length(max=50)],
        filters=[lambda v: v.strip() if v else v],
    )

    Allowed_Dates = StringField(
        "Allowed Dates",
        validators=[Optional(), Length(max=50)],
        filters=[lambda v: v.strip() if v else v],
    )

    Allowed_Routes = StringField(
        "Allowed Routes",
        validators=[
            Optional(),
            Length(max=255),
            Regexp(
                _ROUTE_LIST_PATTERN,
                message=(
                    "Expected comma-separated 3-letter city codes, "
                    "e.g. CGK,SIN"
                ),
            ),
        ],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    is_active = BooleanField("Active", default=True)


class MessageIdentifierForm(FlaskForm):
    Msg_Identifier_Code = StringField(
        "Message Identifier Code",
        validators=[DataRequired(), Length(min=3, max=3)],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    Description = StringField(
        "Description",
        validators=[Optional(), Length(max=255)],
        filters=[lambda v: v.strip() if v else v],
    )