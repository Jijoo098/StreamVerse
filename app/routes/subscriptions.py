"""Subscription-related routes"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import stripe
from app import db
from app.models import SubscriptionPlan, UserSubscription, Payment
from app.utils import get_active_subscription

bp = Blueprint('subscriptions', __name__, url_prefix='')


@bp.route('/subscriptions', endpoint='subscriptions')
@login_required
def subscriptions():
    """View subscription plans"""
    plans = SubscriptionPlan.query.order_by(SubscriptionPlan.price.asc()).all()
    active = get_active_subscription(current_user)
    return render_template('subscriptions.html', plans=plans, active=active)


@bp.route('/subscribe/<int:plan_id>', methods=['GET', 'POST'])
@login_required
def subscribe(plan_id):
    """Subscribe to a plan"""
    plan = SubscriptionPlan.query.get_or_404(plan_id)
    if request.method == 'POST':
        # If Stripe is configured, start checkout
        stripe_secret_key = current_app.config.get('STRIPE_SECRET_KEY')
        if stripe_secret_key:
            stripe.api_key = stripe_secret_key
            try:
                session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=[{
                        'price_data': {
                            'currency': 'usd',
                            'product_data': {
                                'name': plan.name
                            },
                            'unit_amount': int(plan.price * 100)
                        },
                        'quantity': 1
                    }],
                    mode='payment',
                    success_url=url_for('subscriptions.subscriptions', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
                    cancel_url=url_for('subscriptions.subscriptions', _external=True),
                    metadata={'user_id': current_user.id, 'plan_id': plan.id}
                )
                return redirect(session.url)
            except Exception as e:
                print('Stripe error:', e)

        # Fallback (mock) subscription mode if stripe not configured
        now = datetime.utcnow()
        end = now + timedelta(days=plan.duration_days)
        sub = UserSubscription(user_id=current_user.id, plan_id=plan.id, start_date=now, end_date=end)
        db.session.add(sub)
        # Record a simple payment record (mock)
        payment = Payment(user_id=current_user.id, amount=plan.price, status='Completed')
        db.session.add(payment)
        db.session.commit()
        flash(f'Subscribed to {plan.name} successfully! 🎉', 'success')
        return redirect(url_for('dashboard'))
    return render_template('subscribe_confirm.html', plan=plan)


@bp.route('/subscription/cancel', methods=['POST'])
@login_required
def cancel_subscription():
    """Cancel active subscription"""
    active = get_active_subscription(current_user)
    if active:
        active.end_date = datetime.utcnow()
        db.session.commit()
        flash('Subscription canceled. You will continue to have access until the period ends.', 'info')
    else:
        flash('No active subscription found.', 'warning')
    return redirect(url_for('subscriptions.subscriptions'))


@bp.route('/stripe/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events"""
    webhook_secret = current_app.config.get('STRIPE_WEBHOOK_SECRET')
    if not webhook_secret:
        return 'Webhook not configured', 400
    
    stripe_secret_key = current_app.config.get('STRIPE_SECRET_KEY')
    if stripe_secret_key:
        stripe.api_key = stripe_secret_key
    
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError as e:
        return '', 400
    except stripe.error.SignatureVerificationError:
        return '', 400

    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        metadata = session.get('metadata', {}) or {}
        user_id = int(metadata.get('user_id', 0))
        plan_id = int(metadata.get('plan_id', 0))
        # Create the UserSubscription and Payment records
        try:
            plan = SubscriptionPlan.query.get(plan_id)
            if plan and user_id:
                now = datetime.utcnow()
                end = now + timedelta(days=plan.duration_days)
                s = UserSubscription(user_id=user_id, plan_id=plan.id, start_date=now, end_date=end)
                db.session.add(s)
                p = Payment(user_id=user_id, amount=plan.price, status='Completed')
                db.session.add(p)
                db.session.commit()
        except Exception as e:
            print('Error creating subscription from webhook:', e)

    return '', 200

