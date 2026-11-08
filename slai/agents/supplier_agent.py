from __future__ import annotations



from typing import Any




from slai.core.agent_protocol import (
    AgentRequest,
    AgentResponse,
)




from slai.core.models import SupplierAgentResult




class SupplierAgent:
    name = "supplier_agent"
    description = (
        "Проверяет поставщика, его документы, "
        "производственные мощности и риски"
    )
    allowed_skills = ()



    def run(
        self,
        deal_id: int,
        deal: dict[str, Any],
        documents: list[dict[str, Any]],
    ) -> AgentResponse:
        request = AgentRequest(
            agent=self.name,
            task="check_supplier",
            context={
                "deal_id": deal_id,
                "deal": deal,
                "documents": documents,
            },
        )



        try:
            supplier_name = str(
                deal.get("supplier_name", "")
            ).strip()



            missing_information: list[str] = []
            risks: list[dict[str, Any]] = []
            next_actions: list[str] = []
            certificates: list[str] = []
            evidence: list[dict[str, Any]] = []



            if not supplier_name:
                missing_information.append(
                    "Наименование поставщика не указано"
                )



            contract_documents = [
                document
                for document in documents
                if document.get("document_type") == "contract"
            ]



            quality_documents = [
                document
                for document in documents
                if document.get("document_type") == "quality"
            ]



            other_documents = [
                document
                for document in documents
                if document.get("document_type") == "other"
            ]



            if not contract_documents:
                missing_information.append(
                    "Договор с поставщиком не предоставлен"
                )



                risks.append(
                    {
                        "title": "Риск работы без договора",
                        "description": (
                            "Отсутствует договор, определяющий условия поставки, "
                            "оплаты и ответственности сторон."
                        ),
                        "severity": "high",
                        "source": "SUP-001",
                    }
                )



                next_actions.append(
                    "Загрузить или запросить договор поставщика"
                )



            if not quality_documents:
                missing_information.append(
                    "Документы о качестве или сертификаты не предоставлены"
                )



                next_actions.append(
                    "Запросить сертификаты качества и документы на товар"
                )



            factory_verified = bool(
                quality_documents or other_documents
            )



            if not factory_verified:
                risks.append(
                    {
                        "title": "Неподтверждённое производство",
                        "description": (
                            "Производственные мощности и документы поставщика "
                            "не подтверждены."
                        ),
                        "severity": "medium",
                        "source": "SUP-002",
                    }
                )



                next_actions.append(
                    "Запросить фото, видео или отчёт о производстве"
                )



            relevant_documents = (
                contract_documents
                + quality_documents
                + other_documents
            )



            seen_files = set()



            for document in relevant_documents:
                file_name = document.get(
                    "file_name",
                    "",
                )



                if not file_name:
                    continue



                if file_name.lower().startswith(
                    ("test_", "test-")
                ):
                    continue



                if file_name in seen_files:
                    continue



                seen_files.add(file_name)



                if (
                    document.get("document_type")
                    == "quality"
                ):
                    certificates.append(file_name)



                evidence.append(
                    {
                        "type": "document",
                        "file_name": file_name,
                        "document_type": document.get(
                            "document_type",
                            "",
                        ),
                    }
                )



            if missing_information:
                risk_level = "medium"



                if any(
                    risk.get("severity") == "high"
                    for risk in risks
                ):
                    risk_level = "high"



            else:
                risk_level = "low"



            supplier_status = (
                "approved"
                if not missing_information
                else "needs_review"
            )



            result = SupplierAgentResult(
                supplier_status=supplier_status,
                risk_level=risk_level,
                company_verified=bool(supplier_name),
                factory_verified=factory_verified,
                certificates=certificates,
                missing_information=missing_information,
                risks=risks,
                next_actions=next_actions,
                sources=list(seen_files),
            )



            confidence = (
                0.85
                if contract_documents and factory_verified
                else 0.65
            )



            return AgentResponse(
                agent=self.name,
                status="completed",
                data=result.to_dict(),
                confidence=confidence,
                evidence=evidence,
                warnings=[],
                requires_human_review=(
                    supplier_status == "needs_review"
                ),
                model=None,
                prompt_version=request.prompt_version,
                error=None,
            )



        except Exception as error:
            return AgentResponse(
                agent=self.name,
                status="failed",
                data={},
                confidence=0.0,
                evidence=[],
                warnings=[],
                requires_human_review=True,
                model=None,
                prompt_version=request.prompt_version,
                error=str(error),
            )