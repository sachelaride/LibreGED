from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.models import Base, utc_now


class FinancialContract(Base):
    __tablename__ = "financial_contracts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('em_validacao', 'ativo', 'cancelado')",
            name="ck_financial_contract_status",
        ),
        CheckConstraint(
            "total_amount >= 0 AND discount >= 0 AND discount <= total_amount",
            name="ck_financial_contract_amounts",
        ),
        Index(
            "ix_financial_contract_scope",
            "institution_id",
            "student_id",
            "course_id",
        ),
    )

    id = Column(String, primary_key=True, index=True)
    institution_id = Column(
        String,
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    student_id = Column(
        String,
        ForeignKey("students.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    responsible_financial_id = Column(
        String,
        ForeignKey("guardians.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    enrollment_id = Column(
        String,
        ForeignKey("enrollments.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    course_id = Column(
        String,
        ForeignKey("academic_courses.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    period = Column(String(40), nullable=True)
    status = Column(String(30), nullable=False, default="em_validacao")
    plan = Column(String(120), nullable=False)
    total_amount = Column(Numeric(12, 2), nullable=False)
    discount = Column(Numeric(12, 2), nullable=False, default=0)
    responsible_financial = Column(String(160), nullable=False)
    signed_at = Column(Date, nullable=True)
    created_by = Column(
        String,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at = Column(DateTime, nullable=False, default=utc_now)

    institution = relationship("Institution")
    student = relationship("Student")
    responsible_financial_person = relationship("Guardian")
    enrollment = relationship("Enrollment")
    course = relationship("AcademicCourse")
    creator = relationship("User")
    invoices = relationship(
        "FinancialInvoice",
        back_populates="contract",
        cascade="all, delete-orphan",
    )


class FinancialInvoice(Base):
    __tablename__ = "financial_invoices"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pendente', 'atrasado', 'vencido', 'quitado', 'cancelado')",
            name="ck_financial_invoice_status",
        ),
        CheckConstraint("amount > 0", name="ck_financial_invoice_amount"),
        Index(
            "ix_financial_invoice_scope",
            "institution_id",
            "student_id",
            "course_id",
            "due_date",
        ),
    )

    id = Column(String, primary_key=True, index=True)
    institution_id = Column(
        String,
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    student_id = Column(
        String,
        ForeignKey("students.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    responsible_financial_id = Column(
        String,
        ForeignKey("guardians.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    contract_id = Column(
        String,
        ForeignKey("financial_contracts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    enrollment_id = Column(
        String,
        ForeignKey("enrollments.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    course_id = Column(
        String,
        ForeignKey("academic_courses.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    amount = Column(Numeric(12, 2), nullable=False)
    due_date = Column(Date, nullable=False)
    status = Column(String(30), nullable=False, default="pendente")
    payment_recorded_at = Column(DateTime, nullable=True)
    issuer = Column(String(120), nullable=False)
    payment_method = Column(String(40), nullable=False)
    installment = Column(String(40), nullable=False)
    responsible_financial = Column(String(160), nullable=False)
    created_by = Column(
        String,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at = Column(DateTime, nullable=False, default=utc_now)

    institution = relationship("Institution")
    student = relationship("Student")
    responsible_financial_person = relationship("Guardian")
    contract = relationship("FinancialContract", back_populates="invoices")
    enrollment = relationship("Enrollment")
    course = relationship("AcademicCourse")
    creator = relationship("User")


class FinancialAcademicReview(Base):
    __tablename__ = "financial_academic_reviews"
    __table_args__ = (
        CheckConstraint(
            "review_type IN ('transferencia')",
            name="ck_financial_academic_review_type",
        ),
        CheckConstraint(
            "status IN ('pendente', 'resolvida')",
            name="ck_financial_academic_review_status",
        ),
        UniqueConstraint(
            "enrollment_id",
            "review_type",
            name="uq_financial_academic_review_enrollment_type",
        ),
        Index(
            "ix_financial_academic_review_scope",
            "institution_id",
            "student_id",
            "status",
        ),
    )

    id = Column(String, primary_key=True, index=True)
    institution_id = Column(
        String,
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    student_id = Column(
        String,
        ForeignKey("students.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    enrollment_id = Column(
        String,
        ForeignKey("enrollments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    review_type = Column(String(40), nullable=False)
    status = Column(String(30), nullable=False, default="pendente")
    details = Column(String(1000), nullable=False)
    created_by = Column(
        String,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    resolved_by = Column(
        String,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    resolution_note = Column(String(2000), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    resolved_at = Column(DateTime, nullable=True)

    institution = relationship("Institution")
    student = relationship("Student")
    enrollment = relationship("Enrollment")
    creator = relationship("User", foreign_keys=[created_by])
    resolver = relationship("User", foreign_keys=[resolved_by])
