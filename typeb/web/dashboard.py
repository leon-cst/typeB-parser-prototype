"""
Agreement Table CRUD GUI.

Plain HTML for now (no Skote styling yet). Soft-delete only: the
"delete" route flips is_active to False rather than removing the row,
since this is a config table that affects reply generation and past
state is worth keeping.
"""
from flask import Blueprint, abort, flash, redirect, render_template, url_for

from typeb.extensions import db
from typeb.db.models import Agreement, MessageIdentifier, InventoryAvailability, Pnr
from typeb.web.forms import AgreementForm, MessageIdentifierForm, InventoryAvailabilityForm, PnrForm
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