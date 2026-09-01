from collections import defaultdict

from odoo import models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    def _qms_accessible(self, operation="read"):
        model_docid_actids = defaultdict(lambda: defaultdict(list))
        for activity in self.sudo():
            if activity.res_model and activity.res_model.startswith("pm.qms."):
                model_docid_actids[activity.res_model][activity.res_id].append(activity.id)

        qms_ids = {
            activity_id
            for docid_actids in model_docid_actids.values()
            for activity_ids in docid_actids.values()
            for activity_id in activity_ids
        }
        allowed_qms_ids = set()
        for doc_model, docid_actids in model_docid_actids.items():
            if doc_model not in self.env.registry.models:
                continue
            allowed = self.env["mail.message"]._filter_records_for_message_operation(
                doc_model, docid_actids, operation
            )
            allowed_document_ids = set(allowed.ids)
            allowed_qms_ids.update(
                activity_id
                for document_id, activity_ids in docid_actids.items()
                if document_id in allowed_document_ids
                for activity_id in activity_ids
            )
        allowed_ids = (set(self.ids) - qms_ids) | allowed_qms_ids
        return self.browse(
            activity_id for activity_id in self.ids if activity_id in allowed_ids
        )

    def _check_access(self, operation):
        """Apply the related QMS document boundary to assigned activities too.

        Odoo permits a user to read an activity assigned to them without
        checking the related document. That exception is useful for ordinary
        Odoo records, but would disclose a scoped QMS record through its
        activity. Native mail behavior remains unchanged for non-QMS models.
        """
        result = super()._check_access(operation)
        if not self:
            return result

        allowed_ids = self._qms_accessible(operation).ids
        forbidden_ids = [activity_id for activity_id in self.ids if activity_id not in allowed_ids]

        if not forbidden_ids:
            return result
        forbidden = self.browse(forbidden_ids)
        if result:
            return (result[0] + forbidden, result[1])
        return (forbidden, lambda: forbidden._make_access_error(operation))

    def read(self, fields=None, load="_classic_read"):
        if not self.env.su:
            self.check_access("read")
        return super().read(fields=fields, load=load)

    def search(self, domain=None, offset=0, limit=None, order=None):
        records = super().search(domain, offset=0, limit=None, order=order)
        if self.env.su:
            return records[offset:][:limit] if limit else records[offset:]
        accessible = records._qms_accessible("read")
        if offset:
            accessible = accessible[offset:]
        return accessible[:limit] if limit else accessible

    def search_count(self, domain, limit=None):
        if self.env.su:
            return super().search_count(domain, limit=limit)
        return len(self.search(domain, limit=limit))
