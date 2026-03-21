from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from extensions import db
from models import ScoreConfig

pontuacao_bp = Blueprint("pontuacao", __name__)


@pontuacao_bp.route("/pontuacao")
def pontuacao():
    rows = ScoreConfig.query.order_by(ScoreConfig.placement).all()
    return render_template("pontuacao.html", rows=rows)


@pontuacao_bp.route("/pontuacao/save", methods=["POST"])
def save():
    """
    Recebe JSON: [ {"placement": 1, "points": 10}, … ]
    Substitui toda a tabela score_config.
    """
    data = request.get_json(silent=True)
    if not data or not isinstance(data, list):
        return jsonify({"ok": False, "error": "Payload inválido."}), 400

    # Validação básica
    seen = set()
    for entry in data:
        try:
            placement = int(entry["placement"])
            points    = int(entry["points"])
        except (KeyError, ValueError, TypeError):
            return jsonify({"ok": False, "error": "Valores inválidos na tabela."}), 400

        if placement < 1:
            return jsonify({"ok": False, "error": f"Colocação inválida: {placement}."}), 400
        if points < 0:
            return jsonify({"ok": False, "error": f"Pontos negativos não são permitidos."}), 400
        if placement in seen:
            return jsonify({"ok": False, "error": f"Colocação {placement}º duplicada."}), 400
        seen.add(placement)

    # Persiste
    ScoreConfig.query.delete()
    for entry in data:
        db.session.add(ScoreConfig(
            placement=int(entry["placement"]),
            points=int(entry["points"]),
        ))
    db.session.commit()

    return jsonify({"ok": True, "saved": len(data)})


@pontuacao_bp.route("/pontuacao/reset", methods=["POST"])
def reset():
    """Restaura a pontuação padrão."""
    defaults = {1: 10, 2: 8, 3: 7, 4: 6, 5: 5, 6: 4, 7: 3, 8: 2, 9: 1}
    ScoreConfig.query.delete()
    for placement, points in defaults.items():
        db.session.add(ScoreConfig(placement=placement, points=points))
    db.session.commit()
    flash("Pontuação restaurada para os valores padrão.", "success")
    return redirect(url_for("pontuacao.pontuacao"))
