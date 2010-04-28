"""Model managers used by the pages application."""


from __future__ import with_statement

import threading, contextlib

from django.contrib.sites.models import Site
from django.db import models


class PublicationManagementError(Exception):
    
    """
    Exception thrown when something goes wrong with publication management.
    """


class PublicationManager(threading.local):
    
    """
    Tracks a thread-local state of whether querysets should be filtered based on
    publication state.
    
    By default, unpublished content will be filtered out.
    """
    
    def __init__(self):
        """Initializes the PublicationManager."""
        self._stack = []
        
    def _begin(self, select_published):
        """Starts a block using the given publication setting."""
        self._stack.append(select_published)
        
    def select_published_active(self):
        """
        Returns True if querysets should be filtered to exclude unpublished
        content.
        """
        try:
            return self._stack[-1]
        except IndexError:
            return True
        
    def _end(self):
        """Ends a block of publication control."""
        try:
            self._stack.pop()
        except IndexError:
            raise PublicationManagementError, "There is no active block of publication management."
        
    @contextlib.contextmanager
    def select_published(self, select_published):
        """Marks a block of publication management."""
        self._begin(select_published)
        try:
            yield
        except:
            raise
        finally:
            self._end()
            
    
# A single, thread-safe publication manager.
publication_manager = PublicationManager()


class PublishedModelManager(models.Manager):
    
    """Manager that fetches published models."""
    
    use_for_related_fields = True
    
    def get_query_set(self):
        """"Returns the queryset, filtered if appropriate."""
        queryset = super(PublishedModelManager, self).get_query_set()
        if publication_manager.select_published_active():
            queryset = self.model.select_published(queryset)
        return queryset
    
    
class PageBaseManager(PublishedModelManager):
    
    """Base managed for pages."""
    
    def get_query_set(self):
        """Returns the filtered query set."""
        queryset = super(PageBaseManager, self).get_query_set()
        queryset = queryset.filter(site=Site.objects.get_current())
        return queryset        