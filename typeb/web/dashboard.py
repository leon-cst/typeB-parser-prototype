"""
Agreement Table CRUD GUI.

Plain HTML for now (no Skote styling yet). Soft-delete only: the
"delete" route flips is_active to False rather than removing the row,
since this is a config table that affects reply generation and past
state is worth keeping.
"""
from flask import Blueprint, abort, flash, redirect, render_template, url_for

from typeb.extensions import db
from typeb.db.models import Agreement, MessageIdentifier
from typeb.web.forms import AgreementForm, MessageIdentifierForm

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