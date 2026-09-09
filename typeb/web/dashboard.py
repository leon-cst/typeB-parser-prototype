"""
Agreement Table CRUD GUI.

Plain HTML for now (no Skote styling yet). Soft-delete only: the
"delete" route flips is_active to False rather than removing the row,
since this is a config table that affects reply generation and past
state is worth keeping.
"""
from flask import Blueprint, abort, flash, redirect, render_template, url_for

from typeb.db.models import Agreement
from typeb.extensions import db
from typeb.web.forms import AgreementForm

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