"""Core models used by the CMS."""


import datetime

from django.conf import settings
from django.db import models
from django.db.models import Q

from cms.apps.pages import content
from cms.apps.pages.optimizations import cached_getter, cached_setter
from cms.apps.pages.models.base import PublishedModel, PageBase
from cms.apps.pages.models.managers import PublishedModelManager, PageBaseManager, PageManager, cache, publication_manager
from cms.apps.pages.models.fields import PageField, HtmlField, NullBooleanField, EnumField


class Page(PageBase):

    """A page within the site."""

    objects = PageManager()
    
    @classmethod
    def select_published(cls, queryset):
        """Selects only published pages."""
        queryset = super(Page, cls).select_published(queryset)
        now = datetime.datetime.now()
        queryset = queryset.filter(Q(publication_date=None) | Q(publication_date__lte=now))
        queryset = queryset.filter(Q(expiry_date=None) | Q(expiry_date__gt=now))
        return queryset
    
    # Base fields.
    
    url_title = models.SlugField("URL title",
                                 db_index=False)

    def __init__(self, *args, **kwargs):
        """"Initializes the Page."""
        super(Page, self).__init__(*args, **kwargs)
        if self.id:
            cache.add(self)
    
    # Hierarchy fields.

    parent = PageField(blank=True,
                       null=True)

    def get_all_parents(self):
        """Returns a list of all parents of this page."""
        if self.parent:
            return [self.parent] + self.parent.all_parents
        return []
    
    all_parents = property(get_all_parents,
                           doc="A list of all parents of this page.")

    order = models.PositiveIntegerField(unique=True,
                                        editable=False,
                                        blank=True,
                                        null=True)

    @cached_getter
    def get_children(self):
        """
        Returns all the children of this page, regardless of their publication
        state.
        """
        return Page.objects.filter(parent=self)
    
    children = property(get_children,
                        doc="All children of this page.")
    
    def get_all_children(self):
        """
        Returns all the children of this page, cascading down to their children
        too.
        """
        children = []
        for child in self.children:
            children.append(child)
            children.extend(child.all_children)
        return children
            
    all_children = property(get_all_children,
                            doc="All the children of this page, cascading down to their children too.")
    
    # Publication fields.
    
    publication_date = models.DateTimeField(blank=True,
                                            null=True,
                                            help_text="The date that this page will appear on the website.  Leave this blank to immediately publish this page.")

    expiry_date = models.DateTimeField(blank=True,
                                       null=True,
                                       help_text="The date that this page will be removed from the website.  Leave this blank to never expire this page.")

    # Navigation fields.

    in_navigation = models.BooleanField("add to navigation",
                                        default=True,
                                        help_text="Uncheck this box to remove this content from the site navigation.")

    @cached_getter
    def get_navigation(self):
        """
        Returns all published children that should be added to the navigation.
        """
        return self.children.filter(in_navigation=True)
        
    navigation = property(get_navigation,
                          doc="All published children that should be added to the navigation.")

    permalink = models.SlugField(blank=True,
                                 help_text="A unique identifier for this page.  This will be set by your design team in order to link to this page from any custom templates they write.")

    # Content fields.
    
    content_type = models.CharField(max_length=20,
                                    editable=False,
                                    db_index=True,
                                    help_text="The type of page content.")

    content_data = models.TextField(editable=False,
                                    help_text="The encoded data of this page.")
    
    @cached_getter
    def get_content(self):
        """Returns the content object associated with this page."""
        if not self.content_type:
            return None
        content_cls = content.lookup(self.content_type)
        content_instance = content_cls(self)
        return content_instance

    @cached_setter(get_content)
    def set_content(self, content):
        """Sets the content object for this page."""
        self.content_data = content.serialized_data

    content = property(get_content,
                       set_content,
                       doc="The content object associated with this page.")

    # Standard model methods.
    
    def get_absolute_url(self):
        """Generates the absolute url of the page."""
        if self.parent:
            return self.parent.url + self.url_title + "/"
        return "/"
    
    def save(self, *args, **kwargs):
        """Saves the page."""
        super(Page, self).save(*args, **kwargs)
        cache.add(self)
        
    def delete(self, *args, **kwargs):
        """Deletes the page."""
        super(Page, self).delete(*args, **kwargs)
        cache.remove(self)
    
    class Meta:
        unique_together = (("parent", "url_title",),)
        ordering = ("order",)
