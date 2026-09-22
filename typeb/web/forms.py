"""
WTForms definitions for the agreement-table CRUD GUI.

"""
import re

from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField, SelectField
from wtforms.validators import DataRequired, Length, Optional, Regexp, NumberRange
from typeb.tables import loader

_PARTNER_CODE_RE = re.compile(r"^[A-Z0-9]{2,10}$")
_FLIGHT_NUMBER_RE = re.compile(r"^[A-Z]{2}\d{3,4}$")
_CITY_CODE_RE = re.compile(r"^[A-Z]{3}$")
_RBD_CLASS_RE = re.compile(r"^[A-Z]$")
_PNR_CODE_RE = re.compile(r"^[A-Z0-9]{5,10}$")
_BOOKING_OFFICE_RE = re.compile(r"^[A-Z0-9]{3,10}$")
_TRAVEL_AGENT_ID_RE = re.compile(r"^\d{1,20}$")
_SSR_CODE_RE = re.compile(r"^[A-Z]{4}$")
_RESPONSE_FORMAT_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
_ALLOWED_DATES_RE = re.compile(r"^\d+_DAYS$")
_ALLOWED_ROUTES_RE = re.compile(r"^(ALL|[A-Z]{3}(,\s*[A-Z]{3})*)$")


class AgreementForm(FlaskForm):
    Partner_Code = StringField(
        "Partner Code",
        validators=[
            DataRequired(),
            Length(max=10),
            Regexp(_PARTNER_CODE_RE, message="Expected 2-10 uppercase letters/digits, e.g. 1A, 1G"),
        ],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    Response_Format_Option = StringField(
        "Response Format Option",
        validators=[
            Optional(),
            Length(max=50),
            Regexp(
                _RESPONSE_FORMAT_RE,
                message="Expected uppercase letters, digits, underscores, e.g. STANDARD_TTY",
            ),
        ],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    Allowed_Dates = StringField(
        "Allowed Dates",
        validators=[
            Optional(),
            Length(max=50),
            Regexp(
                _ALLOWED_DATES_RE,
                message="Expected format N_DAYS, e.g. 365_DAYS",
            ),
        ],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    Allowed_Routes = StringField(
        "Allowed Routes",
        validators=[
            Optional(),
            Length(max=255),
            Regexp(
                _ALLOWED_ROUTES_RE,
                message="Expected ALL or comma-separated 3-letter city codes, e.g. CGK,SIN",
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
        validators=[
            DataRequired(),
            Length(max=10),
            Regexp(_FLIGHT_NUMBER_RE, message="Expected 2 letters + 3-4 digits, e.g. MZ001, BB800"),
        ],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    Flight_Date = StringField(
        "Flight Date (YYYY-MM-DD)",
        validators=[DataRequired()],
        filters=[lambda v: v.strip() if v else v],
    )

    Boarding_Point = StringField(
        "Boarding Point",
        validators=[
            DataRequired(),
            Length(min=3, max=3),
            Regexp(_CITY_CODE_RE, message="Expected exactly 3 uppercase letters, e.g. CGK"),
        ],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    Off_Point = StringField(
        "Off Point",
        validators=[
            DataRequired(),
            Length(min=3, max=3),
            Regexp(_CITY_CODE_RE, message="Expected exactly 3 uppercase letters, e.g. SIN"),
        ],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    RBD_Class = StringField(
        "RBD Class (1 letter)",
        validators=[
            DataRequired(),
            Length(min=1, max=1),
            Regexp(_RBD_CLASS_RE, message="Expected a single uppercase letter, e.g. Y, J, M"),
        ],
        filters=[lambda v: v.strip().upper() if v else v],
    )

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

    def validate_Numeric_Availability(self, field):
        if field.data and not loader.is_valid_numeric_availability(field.data):
            raise ValidationError(
                "Expected format A0-A9 or L0-L9, e.g. A5, L6"
            )

_POS_USER_TYPE_RE = re.compile(r"^[A-Z]$")

class PnrForm(FlaskForm):
    PNR_Code = StringField(
        "PNR Code",
        validators=[
            DataRequired(),
            Length(max=10),
            Regexp(_PNR_CODE_RE, message="Expected 5-10 uppercase letters/digits, e.g. YQHNBA"),
        ],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    Booking_Office_Code = StringField(
        "Booking Office Code",
        validators=[
            DataRequired(),
            Length(max=10),
            Regexp(_BOOKING_OFFICE_RE, message="Expected 3-10 uppercase letters/digits, e.g. JKTBA"),
        ],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    POS_Travel_Agent_ID = StringField(
        "POS Travel Agent ID",
        validators=[Optional(), Length(max=20)],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    POS_City_Code = StringField(
        "POS City Code",
        validators=[
            Optional(),
            Length(min=3, max=3),
            Regexp(_CITY_CODE_RE, message="Expected exactly 3 uppercase letters, e.g. JKT"),
        ],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    POS_User_Type = StringField(
        "POS User Type",
        validators=[
            Optional(),
            Length(min=1, max=1),
            Regexp(_POS_USER_TYPE_RE, message="Expected a single letter, e.g. T (Travel Agent) or A (Airline)"),
        ],
        filters=[lambda v: v.strip().upper() if v else v],
    )


_TITLE_RE = re.compile(r"^[A-Z]{2,4}$")

class PassengerForm(FlaskForm):
    PNR_ID = SelectField(
        "PNR",
        validators=[DataRequired()],
        coerce=int,
        choices=[],
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
        validators=[
            Optional(),
            Length(min=2, max=10),
            Regexp(_TITLE_RE, message="Expected 2-4 uppercase letters, e.g. MR, MRS, DR"),
        ],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    Number_In_Party = StringField(
        "Number in Party",
        validators=[Optional()],
        filters=[lambda v: v.strip() if v else v],
    )

    Passenger_Type = StringField(
        "Passenger Type",
        validators=[Optional(), Length(max=5)],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    Email = StringField(
        "Email",
        validators=[Optional(), Length(max=255)],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    Date_Of_Birth_Raw = StringField(
        "Date of Birth (ddMMMyy)",
        validators=[Optional(), Length(max=10)],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    Foid = StringField(
        "FOID",
        validators=[Optional(), Length(max=50)],
        filters=[lambda v: v.strip().upper() if v else v],
    )

_AIRLINE_CODE_RE = re.compile(r"^[A-Z0-9]{2,3}$")

class FlightSegmentForm(FlaskForm):
    PNR_ID = SelectField(
        "PNR",
        validators=[DataRequired()],
        coerce=int,
        choices=[],
    )

    Airline_Code = StringField(
        "Airline Code",
        validators=[
            Optional(),
            Length(min=2, max=3),
            Regexp(_AIRLINE_CODE_RE, message="Expected 2-3 uppercase letters/digits, e.g. 8G"),
        ],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    Flight_Number = StringField(
        "Flight Number",
        validators=[
            DataRequired(),
            Length(max=10),
            Regexp(_FLIGHT_NUMBER_RE, message="Expected 2 letters + 3-4 digits, e.g. KL0237, BA0123"),
        ],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    RBD_Class = StringField(
        "RBD Class",
        validators=[
            Optional(),
            Length(min=1, max=1),
            Regexp(_RBD_CLASS_RE, message="Expected a single uppercase letter, e.g. F, Y"),
        ],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    Flight_Date = StringField(
        "Flight Date (YYYY-MM-DD)",
        validators=[DataRequired()],
        filters=[lambda v: v.strip() if v else v],
    )

    Boarding_Point = StringField(
        "Boarding Point",
        validators=[
            DataRequired(),
            Length(min=3, max=3),
            Regexp(_CITY_CODE_RE, message="Expected exactly 3 uppercase letters, e.g. CGK"),
        ],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    Off_Point = StringField(
        "Off Point",
        validators=[
            DataRequired(),
            Length(min=3, max=3),
            Regexp(_CITY_CODE_RE, message="Expected exactly 3 uppercase letters, e.g. DPS"),
        ],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    Action_Code = SelectField(
        "Action Code",
        validators=[Optional()],
        choices=[],
    )

    Number_In_Party = StringField(
        "Number in Party",
        validators=[Optional()],
        filters=[lambda v: v.strip() if v else v],
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


class OsiForm(FlaskForm):
    PNR_ID = SelectField(
        "PNR",
        validators=[DataRequired()],
        coerce=int,
        choices=[],
    )

    Passenger_ID = SelectField(
        "Passenger (optional)",
        validators=[Optional()],
        coerce=int,
        choices=[],
    )

    Airline_Code = StringField(
        "Airline Code",
        validators=[
            DataRequired(),
            Length(min=2, max=3),
            Regexp(_AIRLINE_CODE_RE, message="Expected 2-3 uppercase letters/digits, e.g. YY, 8G"),
        ],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    Information_Text = StringField(
        "Information Text",
        validators=[DataRequired(), Length(max=255)],
        filters=[lambda v: v.strip() if v else v],
    )
    

class SsrForm(FlaskForm):
    PNR_ID = SelectField(
        "PNR",
        validators=[DataRequired()],
        coerce=int,
        choices=[],
    )

    Passenger_ID = SelectField(
        "Passenger (optional)",
        validators=[Optional()],
        coerce=int,
        choices=[],
    )

    Segment_ID = SelectField(
        "Flight Segment (optional)",
        validators=[Optional()],
        coerce=int,
        choices=[],
    )

    SSR_Code = StringField(
        "SSR Code",
        validators=[
            DataRequired(),
            Length(min=4, max=4),
            Regexp(_SSR_CODE_RE, message="Expected exactly 4 uppercase letters, e.g. VGML, NSST"),
        ],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    Airline_Code = StringField(
        "Airline Code",
        validators=[
            Optional(),
            Length(min=2, max=2),
            Regexp(_AIRLINE_CODE_RE, message="Expected exactly 2 uppercase letters, e.g. YY, BA"),
        ],
        filters=[lambda v: v.strip().upper() if v else v],
    )

    Action_Code = SelectField(
        "Action Code",
        validators=[Optional()],
        choices=[],  # populated in the route from segment_status_codes.yaml
    )

    Free_Text = StringField(
        "Free Text",
        validators=[Optional(), Length(max=255)],
        filters=[lambda v: v.strip() if v else v],
    )