"""
Agreement Table CRUD GUI.

"""
from flask import Blueprint, abort, flash, redirect, render_template, url_for

from typeb.extensions import db
from typeb.db.models import Agreement, MessageIdentifier, InventoryAvailability, Pnr, Passenger, FlightSegment, Osi, Ssr
from typeb.web.forms import AgreementForm, MessageIdentifierForm, InventoryAvailabilityForm, PnrForm, PassengerForm, FlightSegmentForm, OsiForm, SsrForm
from typeb.tables import loader
from datetime import date

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/agreements")


@dashboard_bp.get("/")
def list_agreements():
    agreements = (
        Agreement.query.order_by(Agreement.Partner_Code, Agreement.Agreement_ID).all()
    )
    return render_template("agreements/list.html", agreements=agreements)


@dashboard_bp.route("/new", methods=["GET", "POST"])
def new_agreement():
    form = AgreementForm()

    if form.validate_on_submit():
        agreement = Agreement(
            Partner_Code=form.Partner_Code.data,
            Response_Format_Option=form.Response_Format_Option.data or None,
            Allowed_Dates=form.Allowed_Dates.data or None,
            Allowed_Routes=form.Allowed_Routes.data or None,
            is_active=form.is_active.data,
        )
        db.session.add(agreement)
        db.session.commit()
        flash(f"Agreement for {agreement.Partner_Code} created.", "success")
        return redirect(url_for("dashboard.list_agreements"))

    return render_template("agreements/form.html", form=form, agreement=None)


@dashboard_bp.route("/<int:agreement_id>/edit", methods=["GET", "POST"])
def edit_agreement(agreement_id):
    agreement = db.session.get(Agreement, agreement_id)
    if agreement is None:
        abort(404)

    form = AgreementForm(obj=agreement)

    if form.validate_on_submit():
        agreement.Partner_Code = form.Partner_Code.data
        agreement.Response_Format_Option = form.Response_Format_Option.data or None
        agreement.Allowed_Dates = form.Allowed_Dates.data or None
        agreement.Allowed_Routes = form.Allowed_Routes.data or None
        agreement.is_active = form.is_active.data
        db.session.commit()
        flash(f"Agreement for {agreement.Partner_Code} updated.", "success")
        return redirect(url_for("dashboard.list_agreements"))

    return render_template("agreements/form.html", form=form, agreement=agreement)


@dashboard_bp.post("/<int:agreement_id>/delete")
def delete_agreement(agreement_id):
    agreement = db.session.get(Agreement, agreement_id)
    if agreement is None:
        abort(404)

    agreement.is_active = False
    db.session.commit()
    flash(f"Agreement for {agreement.Partner_Code} deactivated.", "success")
    return redirect(url_for("dashboard.list_agreements"))

@dashboard_bp.get("/message-identifiers/")
def list_message_identifiers():
    identifiers = MessageIdentifier.query.order_by(MessageIdentifier.Msg_Identifier_Code).all()
    return render_template("message_identifiers/list.html", identifiers=identifiers)


@dashboard_bp.route("/message-identifiers/new", methods=["GET", "POST"])
def new_message_identifier():
    form = MessageIdentifierForm()

    if form.validate_on_submit():
        existing = db.session.get(MessageIdentifier, form.Msg_Identifier_Code.data)
        if existing is not None:
            flash(f"Code {form.Msg_Identifier_Code.data} already exists.", "danger")
            return render_template("message_identifiers/form.html", form=form, identifier=None)

        identifier = MessageIdentifier(
            Msg_Identifier_Code=form.Msg_Identifier_Code.data,
            Description=form.Description.data or None,
        )
        db.session.add(identifier)
        db.session.commit()
        flash(f"Message identifier {identifier.Msg_Identifier_Code} created.", "success")
        return redirect(url_for("dashboard.list_message_identifiers"))

    return render_template("message_identifiers/form.html", form=form, identifier=None)


@dashboard_bp.route("/message-identifiers/<code>/edit", methods=["GET", "POST"])
def edit_message_identifier(code):
    identifier = db.session.get(MessageIdentifier, code)
    if identifier is None:
        abort(404)

    form = MessageIdentifierForm(obj=identifier)

    if form.validate_on_submit():
        identifier.Description = form.Description.data or None
        db.session.commit()
        flash(f"Message identifier {identifier.Msg_Identifier_Code} updated.", "success")
        return redirect(url_for("dashboard.list_message_identifiers"))

    return render_template("message_identifiers/form.html", form=form, identifier=identifier)


@dashboard_bp.post("/message-identifiers/<code>/delete")
def delete_message_identifier(code):
    identifier = db.session.get(MessageIdentifier, code)
    if identifier is None:
        abort(404)

    db.session.delete(identifier)
    db.session.commit()
    flash(f"Message identifier {code} deleted.", "success")
    return redirect(url_for("dashboard.list_message_identifiers"))

def _segment_status_choices():
    entries = loader.segment_status_codes()
    choices = [("", "-- none --")]
    choices += [
        (code, f"{code} — {entry.description}")
        for code, entry in sorted(entries.items(), key=lambda pair: pair[0])
    ]
    return choices


@dashboard_bp.get("/inventory/")
def list_inventory():
    rows = (
        InventoryAvailability.query
        .order_by(InventoryAvailability.Flight_Date, InventoryAvailability.Flight_Number)
        .all()
    )
    return render_template("inventory/list.html", rows=rows)


@dashboard_bp.route("/inventory/new", methods=["GET", "POST"])
def new_inventory():
    form = InventoryAvailabilityForm()
    form.Segment_Status_Code.choices = _segment_status_choices()

    if form.validate_on_submit():
        try:
            flight_date = date.fromisoformat(form.Flight_Date.data)
        except ValueError:
            form.Flight_Date.errors.append("Expected format YYYY-MM-DD.")
            return render_template("inventory/form.html", form=form, row=None)

        row = InventoryAvailability(
            Flight_Number=form.Flight_Number.data,
            Flight_Date=flight_date,
            Boarding_Point=form.Boarding_Point.data,
            Off_Point=form.Off_Point.data,
            RBD_Class=form.RBD_Class.data,
            Segment_Status_Code=form.Segment_Status_Code.data or None,
            Numeric_Availability=form.Numeric_Availability.data or None,
            source="manual",
        )
        db.session.add(row)
        db.session.commit()
        flash(f"Inventory row for {row.Flight_Number} created.", "success")
        return redirect(url_for("dashboard.list_inventory"))

    return render_template("inventory/form.html", form=form, row=None)


@dashboard_bp.route("/inventory/<int:inventory_id>/edit", methods=["GET", "POST"])
def edit_inventory(inventory_id):
    row = db.session.get(InventoryAvailability, inventory_id)
    if row is None:
        abort(404)

    form = InventoryAvailabilityForm(obj=row, Flight_Date=row.Flight_Date.isoformat())
    form.Segment_Status_Code.choices = _segment_status_choices()

    if form.validate_on_submit():
        try:
            flight_date = date.fromisoformat(form.Flight_Date.data)
        except ValueError:
            form.Flight_Date.errors.append("Expected format YYYY-MM-DD.")
            return render_template("inventory/form.html", form=form, row=row)

        row.Flight_Number = form.Flight_Number.data
        row.Flight_Date = flight_date
        row.Boarding_Point = form.Boarding_Point.data
        row.Off_Point = form.Off_Point.data
        row.RBD_Class = form.RBD_Class.data
        row.Segment_Status_Code = form.Segment_Status_Code.data or None
        row.Numeric_Availability = form.Numeric_Availability.data or None
        # source deliberately left untouched -- editing a parser-written
        # row through the manual form doesn't make it a manual row
        db.session.commit()
        flash(f"Inventory row for {row.Flight_Number} updated.", "success")
        return redirect(url_for("dashboard.list_inventory"))

    return render_template("inventory/form.html", form=form, row=row)


@dashboard_bp.post("/inventory/<int:inventory_id>/delete")
def delete_inventory(inventory_id):
    row = db.session.get(InventoryAvailability, inventory_id)
    if row is None:
        abort(404)

    db.session.delete(row)
    db.session.commit()
    flash(f"Inventory row for {row.Flight_Number} deleted.", "success")
    return redirect(url_for("dashboard.list_inventory"))


@dashboard_bp.get("/pnrs/")
def list_pnrs():
    pnrs = Pnr.query.order_by(Pnr.Creation_Date.desc()).all()
    return render_template("pnrs/list.html", pnrs=pnrs)


@dashboard_bp.route("/pnrs/new", methods=["GET", "POST"])
def new_pnr():
    form = PnrForm()

    if form.validate_on_submit():
        pnr = Pnr(
            PNR_Code=form.PNR_Code.data,
            Booking_Office_Code=form.Booking_Office_Code.data,
            POS_Travel_Agent_ID=form.POS_Travel_Agent_ID.data or None,
            POS_City_Code=form.POS_City_Code.data or None,
            POS_User_Type=form.POS_User_Type.data or None,
            source="manual",
        )
        db.session.add(pnr)
        db.session.commit()
        flash(f"PNR {pnr.PNR_Code} created.", "success")
        return redirect(url_for("dashboard.list_pnrs"))

    return render_template("pnrs/form.html", form=form, pnr=None)


@dashboard_bp.route("/pnrs/<int:pnr_id>/edit", methods=["GET", "POST"])
def edit_pnr(pnr_id):
    pnr = db.session.get(Pnr, pnr_id)
    if pnr is None:
        abort(404)

    form = PnrForm(obj=pnr)

    if form.validate_on_submit():
        pnr.PNR_Code = form.PNR_Code.data
        pnr.Booking_Office_Code = form.Booking_Office_Code.data
        pnr.POS_Travel_Agent_ID = form.POS_Travel_Agent_ID.data or None
        pnr.POS_City_Code = form.POS_City_Code.data or None
        pnr.POS_User_Type = form.POS_User_Type.data or None
        # source deliberately untouched -- see InventoryAvailability
        # for the same reasoning
        db.session.commit()
        flash(f"PNR {pnr.PNR_Code} updated.", "success")
        return redirect(url_for("dashboard.list_pnrs"))

    return render_template("pnrs/form.html", form=form, pnr=pnr)


@dashboard_bp.post("/pnrs/<int:pnr_id>/delete")
def delete_pnr(pnr_id):
    pnr = db.session.get(Pnr, pnr_id)
    if pnr is None:
        abort(404)

    db.session.delete(pnr)
    db.session.commit()
    flash(f"PNR {pnr.PNR_Code} deleted.", "success")
    return redirect(url_for("dashboard.list_pnrs"))


def _pnr_choices():
    pnrs = Pnr.query.order_by(Pnr.PNR_Code).all()
    return [(p.PNR_ID, f"{p.PNR_Code} (#{p.PNR_ID})") for p in pnrs]


@dashboard_bp.get("/passengers/")
def list_passengers():
    passengers = Passenger.query.order_by(Passenger.Family_Name).all()
    return render_template("passengers/list.html", passengers=passengers)


@dashboard_bp.route("/passengers/new", methods=["GET", "POST"])
def new_passenger():
    form = PassengerForm()
    form.PNR_ID.choices = _pnr_choices()

    if not form.PNR_ID.choices:
        flash("Create a PNR first before adding passengers.", "danger")
        return redirect(url_for("dashboard.list_pnrs"))

    if form.validate_on_submit():
        number_in_party = None
        if form.Number_In_Party.data:
            try:
                number_in_party = int(form.Number_In_Party.data)
                if number_in_party < 1:
                    raise ValueError
            except ValueError:
                form.Number_In_Party.errors.append("Must be a positive whole number.")
                return render_template("passengers/form.html", form=form, passenger=None)

        passenger = Passenger(
            PNR_ID=form.PNR_ID.data,
            Family_Name=form.Family_Name.data,
            First_Name_Middle_Name=form.First_Name_Middle_Name.data or None,
            Title=form.Title.data or None,
            Number_In_Party=number_in_party,
        )
        db.session.add(passenger)
        db.session.commit()
        flash(f"Passenger {passenger.Family_Name} created.", "success")
        return redirect(url_for("dashboard.list_passengers"))

    return render_template("passengers/form.html", form=form, passenger=None)


@dashboard_bp.route("/passengers/<int:passenger_id>/edit", methods=["GET", "POST"])
def edit_passenger(passenger_id):
    passenger = db.session.get(Passenger, passenger_id)
    if passenger is None:
        abort(404)

    form = PassengerForm(obj=passenger)
    form.PNR_ID.choices = _pnr_choices()

    if form.validate_on_submit():
        number_in_party = None
        if form.Number_In_Party.data:
            try:
                number_in_party = int(form.Number_In_Party.data)
                if number_in_party < 1:
                    raise ValueError
            except ValueError:
                form.Number_In_Party.errors.append("Must be a positive whole number.")
                return render_template("passengers/form.html", form=form, passenger=None)

        passenger.PNR_ID = form.PNR_ID.data
        passenger.Family_Name = form.Family_Name.data
        passenger.First_Name_Middle_Name = form.First_Name_Middle_Name.data or None
        passenger.Title = form.Title.data or None
        passenger.Number_In_Party = number_in_party
        db.session.commit()
        flash(f"Passenger {passenger.Family_Name} updated.", "success")
        return redirect(url_for("dashboard.list_passengers"))

    return render_template("passengers/form.html", form=form, passenger=passenger)


@dashboard_bp.post("/passengers/<int:passenger_id>/delete")
def delete_passenger(passenger_id):
    passenger = db.session.get(Passenger, passenger_id)
    if passenger is None:
        abort(404)

    db.session.delete(passenger)
    db.session.commit()
    flash(f"Passenger {passenger.Family_Name} deleted.", "success")
    return redirect(url_for("dashboard.list_passengers"))


def _parse_optional_time(raw: str | None):
    if not raw:
        return None
    return time.fromisoformat(raw)


@dashboard_bp.get("/segments/")
def list_segments():
    segments = FlightSegment.query.order_by(FlightSegment.Flight_Date).all()
    return render_template("segments/list.html", segments=segments)


@dashboard_bp.route("/segments/new", methods=["GET", "POST"])
def new_segment():
    form = FlightSegmentForm()
    form.PNR_ID.choices = _pnr_choices()
    form.Action_Code.choices = _segment_status_choices()

    if not form.PNR_ID.choices:
        flash("Create a PNR first before adding flight segments.", "danger")
        return redirect(url_for("dashboard.list_pnrs"))

    if form.validate_on_submit():
        try:
            flight_date = date.fromisoformat(form.Flight_Date.data)
        except ValueError:
            form.Flight_Date.errors.append("Expected format YYYY-MM-DD.")
            return render_template("segments/form.html", form=form, segment=None)

        try:
            departure_time = _parse_optional_time(form.Departure_Time.data)
            arrival_time = _parse_optional_time(form.Arrival_Time.data)
        except ValueError:
            form.Departure_Time.errors.append("Expected format HH:MM.")
            return render_template("segments/form.html", form=form, segment=None)

        segment = FlightSegment(
            PNR_ID=form.PNR_ID.data,
            Flight_Number=form.Flight_Number.data,
            RBD_Class=form.RBD_Class.data or None,
            Flight_Date=flight_date,
            Boarding_Point=form.Boarding_Point.data,
            Off_Point=form.Off_Point.data,
            Action_Code=form.Action_Code.data or None,
            Departure_Time=departure_time,
            Arrival_Time=arrival_time,
        )
        db.session.add(segment)
        db.session.commit()
        flash(f"Flight segment {segment.Flight_Number} created.", "success")
        return redirect(url_for("dashboard.list_segments"))

    return render_template("segments/form.html", form=form, segment=None)


@dashboard_bp.route("/segments/<int:segment_id>/edit", methods=["GET", "POST"])
def edit_segment(segment_id):
    segment = db.session.get(FlightSegment, segment_id)
    if segment is None:
        abort(404)

    form = FlightSegmentForm(
        obj=segment,
        Flight_Date=segment.Flight_Date.isoformat(),
        Departure_Time=segment.Departure_Time.isoformat(timespec="minutes") if segment.Departure_Time else "",
        Arrival_Time=segment.Arrival_Time.isoformat(timespec="minutes") if segment.Arrival_Time else "",
    )
    form.PNR_ID.choices = _pnr_choices()
    form.Action_Code.choices = _segment_status_choices()

    if form.validate_on_submit():
        try:
            flight_date = date.fromisoformat(form.Flight_Date.data)
        except ValueError:
            form.Flight_Date.errors.append("Expected format YYYY-MM-DD.")
            return render_template("segments/form.html", form=form, segment=segment)

        try:
            departure_time = _parse_optional_time(form.Departure_Time.data)
            arrival_time = _parse_optional_time(form.Arrival_Time.data)
        except ValueError:
            form.Departure_Time.errors.append("Expected format HH:MM.")
            return render_template("segments/form.html", form=form, segment=segment)

        segment.PNR_ID = form.PNR_ID.data
        segment.Flight_Number = form.Flight_Number.data
        segment.RBD_Class = form.RBD_Class.data or None
        segment.Flight_Date = flight_date
        segment.Boarding_Point = form.Boarding_Point.data
        segment.Off_Point = form.Off_Point.data
        segment.Action_Code = form.Action_Code.data or None
        segment.Departure_Time = departure_time
        segment.Arrival_Time = arrival_time
        db.session.commit()
        flash(f"Flight segment {segment.Flight_Number} updated.", "success")
        return redirect(url_for("dashboard.list_segments"))

    return render_template("segments/form.html", form=form, segment=segment)


@dashboard_bp.post("/segments/<int:segment_id>/delete")
def delete_segment(segment_id):
    segment = db.session.get(FlightSegment, segment_id)
    if segment is None:
        abort(404)

    db.session.delete(segment)
    db.session.commit()
    flash(f"Flight segment {segment.Flight_Number} deleted.", "success")
    return redirect(url_for("dashboard.list_segments"))



@dashboard_bp.get("/osi/")
def list_osi():
    entries = Osi.query.order_by(Osi.OSI_ID.desc()).all()
    return render_template("osi/list.html", entries=entries)


@dashboard_bp.route("/osi/new", methods=["GET", "POST"])
def new_osi():
    form = OsiForm()
    form.PNR_ID.choices = _pnr_choices()

    if not form.PNR_ID.choices:
        flash("Create a PNR first before adding OSI entries.", "danger")
        return redirect(url_for("dashboard.list_pnrs"))

    if form.validate_on_submit():
        entry = Osi(
            PNR_ID=form.PNR_ID.data,
            Airline_Code=form.Airline_Code.data,
            Information_Text=form.Information_Text.data,
        )
        db.session.add(entry)
        db.session.commit()
        flash(f"OSI entry for {entry.Airline_Code} created.", "success")
        return redirect(url_for("dashboard.list_osi"))

    return render_template("osi/form.html", form=form, entry=None)


@dashboard_bp.route("/osi/<int:osi_id>/edit", methods=["GET", "POST"])
def edit_osi(osi_id):
    entry = db.session.get(Osi, osi_id)
    if entry is None:
        abort(404)

    form = OsiForm(obj=entry)
    form.PNR_ID.choices = _pnr_choices()

    if form.validate_on_submit():
        entry.PNR_ID = form.PNR_ID.data
        entry.Airline_Code = form.Airline_Code.data
        entry.Information_Text = form.Information_Text.data
        db.session.commit()
        flash(f"OSI entry for {entry.Airline_Code} updated.", "success")
        return redirect(url_for("dashboard.list_osi"))

    return render_template("osi/form.html", form=form, entry=entry)


@dashboard_bp.post("/osi/<int:osi_id>/delete")
def delete_osi(osi_id):
    entry = db.session.get(Osi, osi_id)
    if entry is None:
        abort(404)

    db.session.delete(entry)
    db.session.commit()
    flash("OSI entry deleted.", "success")
    return redirect(url_for("dashboard.list_osi"))


def _passenger_choices():
    passengers = Passenger.query.order_by(Passenger.Family_Name).all()
    choices = [(0, "-- none --")]
    choices += [(p.Passenger_ID, f"{p.Family_Name} (#{p.Passenger_ID})") for p in passengers]
    return choices


def _segment_choices():
    segments = FlightSegment.query.order_by(FlightSegment.Flight_Date).all()
    choices = [(0, "-- none --")]
    choices += [
        (s.Segment_ID, f"{s.Flight_Number} {s.Flight_Date} (#{s.Segment_ID})")
        for s in segments
    ]
    return choices


@dashboard_bp.get("/ssr/")
def list_ssr():
    entries = Ssr.query.order_by(Ssr.SSR_ID.desc()).all()
    return render_template("ssr/list.html", entries=entries)


@dashboard_bp.route("/ssr/new", methods=["GET", "POST"])
def new_ssr():
    form = SsrForm()
    form.PNR_ID.choices = _pnr_choices()
    form.Passenger_ID.choices = _passenger_choices()
    form.Segment_ID.choices = _segment_choices()
    form.Action_Code.choices = _segment_status_choices()

    if not form.PNR_ID.choices:
        flash("Create a PNR first before adding SSR entries.", "danger")
        return redirect(url_for("dashboard.list_pnrs"))

    if form.validate_on_submit():
        entry = Ssr(
            PNR_ID=form.PNR_ID.data,
            Passenger_ID=form.Passenger_ID.data or None,
            Segment_ID=form.Segment_ID.data or None,
            SSR_Code=form.SSR_Code.data,
            Airline_Code=form.Airline_Code.data or None,
            Action_Code=form.Action_Code.data or None,
            Free_Text=form.Free_Text.data or None,
        )
        db.session.add(entry)
        db.session.commit()
        flash(f"SSR entry {entry.SSR_Code} created.", "success")
        return redirect(url_for("dashboard.list_ssr"))

    return render_template("ssr/form.html", form=form, entry=None)


@dashboard_bp.route("/ssr/<int:ssr_id>/edit", methods=["GET", "POST"])
def edit_ssr(ssr_id):
    entry = db.session.get(Ssr, ssr_id)
    if entry is None:
        abort(404)

    form = SsrForm(
        obj=entry,
        Passenger_ID=entry.Passenger_ID or 0,
        Segment_ID=entry.Segment_ID or 0,
    )
    form.PNR_ID.choices = _pnr_choices()
    form.Passenger_ID.choices = _passenger_choices()
    form.Segment_ID.choices = _segment_choices()
    form.Action_Code.choices = _segment_status_choices()

    if form.validate_on_submit():
        entry.PNR_ID = form.PNR_ID.data
        entry.Passenger_ID = form.Passenger_ID.data or None
        entry.Segment_ID = form.Segment_ID.data or None
        entry.SSR_Code = form.SSR_Code.data
        entry.Airline_Code = form.Airline_Code.data or None
        entry.Action_Code = form.Action_Code.data or None
        entry.Free_Text = form.Free_Text.data or None
        db.session.commit()
        flash(f"SSR entry {entry.SSR_Code} updated.", "success")
        return redirect(url_for("dashboard.list_ssr"))

    return render_template("ssr/form.html", form=form, entry=entry)


@dashboard_bp.post("/ssr/<int:ssr_id>/delete")
def delete_ssr(ssr_id):
    entry = db.session.get(Ssr, ssr_id)
    if entry is None:
        abort(404)

    db.session.delete(entry)
    db.session.commit()
    flash(f"SSR entry {entry.SSR_Code} deleted.", "success")
    return redirect(url_for("dashboard.list_ssr"))
