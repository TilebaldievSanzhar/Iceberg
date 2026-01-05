import re
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import CategorizationRule, Category, Transaction


class CategorizationService:
    def __init__(self, db: Session):
        self.db = db

    def get_rules(self, user_id: UUID) -> List[CategorizationRule]:
        """Get all rules for user (user's + system rules)."""
        return (
            self.db.query(CategorizationRule)
            .filter(
                (CategorizationRule.user_id == user_id) |
                (CategorizationRule.user_id.is_(None))
            )
            .order_by(
                CategorizationRule.user_id.desc().nullslast(),  # User rules first
                CategorizationRule.priority.desc(),
            )
            .all()
        )

    def create_rule(
        self,
        user_id: UUID,
        category_id: UUID,
        pattern: str,
        match_type: str,
        priority: int = 0,
    ) -> CategorizationRule:
        # Verify category exists and belongs to user or is system
        category = self.db.query(Category).filter(
            Category.id == category_id,
            (Category.user_id == user_id) | (Category.is_system == True)
        ).first()
        if not category:
            raise ValueError("Category not found or access denied")

        rule = CategorizationRule(
            user_id=user_id,
            category_id=category_id,
            pattern=pattern,
            match_type=match_type,
            priority=priority,
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def delete_rule(self, rule_id: UUID, user_id: UUID) -> bool:
        rule = self.db.query(CategorizationRule).filter(
            CategorizationRule.id == rule_id,
            CategorizationRule.user_id == user_id,  # Can only delete own rules
        ).first()
        if not rule:
            return False
        self.db.delete(rule)
        self.db.commit()
        return True

    def match_rule(self, rule: CategorizationRule, text: str) -> bool:
        """Check if text matches the rule pattern."""
        if not text:
            return False

        text_lower = text.lower()
        pattern_lower = rule.pattern.lower()

        if rule.match_type == "exact":
            return text_lower == pattern_lower
        elif rule.match_type == "contains":
            return pattern_lower in text_lower
        elif rule.match_type == "regex":
            try:
                return bool(re.search(rule.pattern, text, re.IGNORECASE))
            except re.error:
                return False
        return False

    def categorize_transaction(
        self,
        user_id: UUID,
        description: Optional[str],
        counterparty: Optional[str],
    ) -> Optional[UUID]:
        """Find matching category for transaction based on rules."""
        rules = self.get_rules(user_id)

        for rule in rules:
            # Check description
            if description and self.match_rule(rule, description):
                return rule.category_id
            # Check counterparty
            if counterparty and self.match_rule(rule, counterparty):
                return rule.category_id

        return None

    def recategorize_transactions(
        self,
        user_id: UUID,
        transaction_ids: Optional[List[UUID]] = None,
    ) -> int:
        """Recategorize transactions based on current rules."""
        query = self.db.query(Transaction).join(Transaction.account).filter(
            Transaction.account.has(user_id=user_id),
            Transaction.is_edited == False,  # Only auto-categorize non-edited
        )

        if transaction_ids:
            query = query.filter(Transaction.id.in_(transaction_ids))

        transactions = query.all()
        updated_count = 0

        for transaction in transactions:
            category_id = self.categorize_transaction(
                user_id=user_id,
                description=transaction.description,
                counterparty=transaction.counterparty,
            )
            if category_id and category_id != transaction.category_id:
                transaction.category_id = category_id
                updated_count += 1

        if updated_count > 0:
            self.db.commit()

        return updated_count
