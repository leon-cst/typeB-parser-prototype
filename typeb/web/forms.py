"""
WTForms definitions for the agreement-table CRUD GUI.

Validation here is deliberately permissive on Response_Format_Option
and Allowed_Dates until Parka confirms the valid value sets -- see
typeb/db/models.py for the same caveat on those two columns.
"""
import re

from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField, SelectField
from wtforms.validators import DataRequired, Length, Optional, Regexp, NumberRange

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


class InventoryAvailabilityForm(FlaskForm):
    Flight_Number = StringField(
        "Flight Number",
        validators=[DataRequired(), Length(max=10)],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    Flight_Date = StringField(
        "Flight Date (YYYY-MM-DD)",
        validators=[DataRequired()],
        filters=[lambda v: v.strip() if v else v],
    )

    Boarding_Point = StringField(
        "Boarding Point",
        validators=[DataRequired(), Length(min=3, max=3)],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    Off_Point = StringField(
        "Off Point",
        validators=[DataRequired(), Length(min=3, max=3)],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    RBD_Class = StringField(
        "RBD Class (1 letter)",
        validators=[DataRequired(), Length(min=1, max=1)],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    # choices populated in the route, since it depends on loader.py data
    Segment_Status_Code = SelectField(
        "Segment Status Code",
        validators=[Optional()],
        choices=[],
    )

    Numeric_Availability = StringField(
        "Numeric Availability",
        validators=[Optional(), Length(max=10)],
        filters=[lambda v: v.strip().upper() if v else v],
    )


class PnrForm(FlaskForm):
    PNR_Code = StringField(
        "PNR Code",
        validators=[DataRequired(), Length(max=10)],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    Booking_Office_Code = StringField(
        "Booking Office Code",
        validators=[DataRequired(), Length(max=10)],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    POS_Travel_Agent_ID = StringField(
        "POS Travel Agent ID",
        validators=[Optional(), Length(max=20)],
        filters=[lambda v: v.strip() if v else v],
    )

    POS_City_Code = StringField(
        "POS City Code",
        validators=[Optional(), Length(min=3, max=3)],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    POS_User_Type = StringField(
        "POS User Type",
        validators=[Optional(), Length(max=5)],
        filters=[lambda v: v.strip().upper() if v else v],
    )


class PassengerForm(FlaskForm):
    PNR_ID = SelectField(
        "PNR",
        validators=[DataRequired()],
        coerce=int,
        choices=[],  # populated in the route from real PNR rows
    )

    Family_Name = StringField(
        "Family Name",
        validators=[DataRequired(), Length(max=50)],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    First_Name_Middle_Name = StringField(
        "First / Middle Name",
        validators=[Optional(), Length(max=100)],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    Title = StringField(
        "Title",
        validators=[Optional(), Length(max=10)],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    Number_In_Party = StringField(
        "Number in Party",
        validators=[Optional()],
        filters=[lambda v: v.strip() if v else v],
    )



class FlightSegmentForm(FlaskForm):
    PNR_ID = SelectField(
        "PNR",
        validators=[DataRequired()],
        coerce=int,
        choices=[],
    )

    Flight_Number = StringField(
        "Flight Number",
        validators=[DataRequired(), Length(max=10)],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    RBD_Class = StringField(
        "RBD Class",
        validators=[Optional(), Length(min=1, max=1)],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    Flight_Date = StringField(
        "Flight Date (YYYY-MM-DD)",
        validators=[DataRequired()],
        filters=[lambda v: v.strip() if v else v],
    )

    Boarding_Point = StringField(
        "Boarding Point",
        validators=[DataRequired(), Length(min=3, max=3)],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    Off_Point = StringField(
        "Off Point",
        validators=[DataRequired(), Length(min=3, max=3)],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    Action_Code = StringField(
        "Action Code",
        validators=[Optional(), Length(min=2, max=2)],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    Departure_Time = StringField(
        "Departure Time (HH:MM)",
        validators=[Optional()],
        filters=[lambda v: v.strip() if v else v],
    )

    Arrival_Time = StringField(
        "Arrival Time (HH:MM)",
        validators=[Optional()],
        filters=[lambda v: v.strip() if v else v],
    )