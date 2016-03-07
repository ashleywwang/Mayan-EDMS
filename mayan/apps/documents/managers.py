from __future__ import unicode_literals

from datetime import timedelta
import logging

from django.apps import apps
from django.conf import settings
from django.db import models
from django.utils.timezone import now

from .literals import STUB_EXPIRATION_INTERVAL
from .settings import setting_recent_count

logger = logging.getLogger(__name__)


class DocumentManager(models.Manager):
    def delete_stubs(self):
        for stale_stub_document in self.filter(is_stub=True, date_added__lt=now() - timedelta(seconds=STUB_EXPIRATION_INTERVAL)):
            stale_stub_document.delete(trash=False)

    def get_by_natural_key(self, uuid):
        return self.get(uuid=uuid)

    def get_queryset(self):
        return TrashCanQuerySet(
            self.model, using=self._db
        ).filter(in_trash=False)

    def invalidate_cache(self):
        for document in self.model.objects.all():
            document.invalidate_cache()


class DocumentTypeManager(models.Manager):
    def check_delete_periods(self):
        logger.info('Executing')

        for document_type in self.all():
            logger.info(
                'Checking deletion period of document type: %s', document_type
            )
            if document_type.delete_time_period and document_type.delete_time_unit:
                delta = timedelta(
                    **{
                        document_type.delete_time_unit: document_type.delete_time_period
                    }
                )
                logger.info(
                    'Document type: %s, has a deletion period delta of: %s',
                    document_type, delta
                )
                for document in document_type.deleted_documents.filter(deleted_date_time__lt=now() - delta):
                    logger.info(
                        'Document "%s" with id: %d, trashed on: %s, exceded '
                        'delete period', document, document.pk,
                        document.deleted_date_time
                    )
                    document.delete()
            else:
                logger.info(
                    'Document type: %s, has a no retention delta', document_type
                )

        logger.info('Finshed')

    def check_trash_periods(self):
        logger.info('Executing')

        for document_type in self.all():
            logger.info(
                'Checking trash period of document type: %s', document_type
            )
            if document_type.trash_time_period and document_type.trash_time_unit:
                delta = timedelta(
                    **{
                        document_type.trash_time_unit: document_type.trash_time_period
                    }
                )
                logger.info(
                    'Document type: %s, has a trash period delta of: %s',
                    document_type, delta
                )
                for document in document_type.documents.filter(date_added__lt=now() - delta):
                    logger.info(
                        'Document "%s" with id: %d, added on: %s, exceded '
                        'trash period', document, document.pk,
                        document.date_added
                    )
                    document.delete()
            else:
                logger.info(
                    'Document type: %s, has a no retention delta', document_type
                )

        logger.info('Finshed')

    def get_by_natural_key(self, label):
        return self.get(label=label)


class NewVersionBlockManager(models.Manager):
    def block(self, document):
        self.get_or_create(document=document)

    def unblock(self, document):
        self.filter(document=document).delete()

    def is_blocked(self, document):
        return self.filter(document=document).exists()


class PassthroughManager(models.Manager):
    pass


class RecentDocumentManager(models.Manager):
    def add_document_for_user(self, user, document):
        if user.is_authenticated():
            new_recent, created = self.model.objects.get_or_create(
                user=user, document=document
            )
            if not created:
                # document already in the recent list, just save to force
                # accessed date and time update
                new_recent.save()

            recent_to_delete = self.filter(user=user).values_list('pk', flat=True)[setting_recent_count.value:]
            self.filter(pk__in=list(recent_to_delete)).delete()

    def get_for_user(self, user):
        document_model = apps.get_model('documents', 'document')

        if user.is_authenticated():
            return document_model.objects.filter(
                recentdocument__user=user,
                document_type__organization__id=settings.ORGANIZATION_ID
            ).order_by('-recentdocument__datetime_accessed')
        else:
            return document_model.objects.none()


class TrashCanManager(models.Manager):
    def get_queryset(self):
        return super(
            TrashCanManager, self
        ).get_queryset().filter(in_trash=True)


class TrashCanQuerySet(models.QuerySet):
    def delete(self, to_trash=True):
        for instance in self:
            instance.delete(to_trash=to_trash)
