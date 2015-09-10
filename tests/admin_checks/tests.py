from __future__ import unicode_literals

from django import forms
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.contenttypes.admin import GenericStackedInline
from django.core import checks
from django.test import SimpleTestCase, override_settings

from .models import Album, Book, City, Influence, Song, State, TwoAlbumFKAndAnE


class SongForm(forms.ModelForm):
    pass


class ValidFields(admin.ModelAdmin):
    form = SongForm
    fields = ['title']


class ValidFormFieldsets(admin.ModelAdmin):
    def get_form(self, request, obj=None, **kwargs):
        class ExtraFieldForm(SongForm):
            name = forms.CharField(max_length=50)
        return ExtraFieldForm

    fieldsets = (
        (None, {
            'fields': ('name',),
        }),
    )


class MyAdmin(admin.ModelAdmin):
    def check(self, **kwargs):
        return ['error!']


@override_settings(
    SILENCED_SYSTEM_CHECKS=['fields.W342'],  # ForeignKey(unique=True)
    INSTALLED_APPS=['django.contrib.auth', 'django.contrib.contenttypes', 'admin_checks']
)
class SystemChecksTestCase(SimpleTestCase):

    @override_settings(DEBUG=True)
    def test_checks_are_performed(self):
        admin.site.register(Song, MyAdmin)
        try:
            errors = checks.run_checks()
            expected = ['error!']
            self.assertEqual(errors, expected)
        finally:
            admin.site.unregister(Song)
            admin.sites.system_check_errors = []

    @override_settings(DEBUG=True)
    def test_custom_adminsite(self):
        class CustomAdminSite(admin.AdminSite):
            pass

        custom_site = CustomAdminSite()
        custom_site.register(Song, MyAdmin)
        try:
            errors = checks.run_checks()
            expected = ['error!']
            self.assertEqual(errors, expected)
        finally:
            custom_site.unregister(Song)
            admin.sites.system_check_errors = []

    def test_field_name_not_in_list_display(self):
        class SongAdmin(admin.ModelAdmin):
            list_editable = ["original_release"]

        site = AdminSite()
        errors = SongAdmin(Song, site).check()
        expected = [
            checks.Error(
                "The value of 'list_editable[0]' refers to 'original_release', "
                "which is not contained in 'list_display'.",
                hint=None,
                obj=SongAdmin,
                id='admin.E122',
            )
        ]
        self.assertEqual(errors, expected)

    def test_readonly_and_editable(self):
        class SongAdmin(admin.ModelAdmin):
            readonly_fields = ["original_release"]
            list_display = ["pk", "original_release"]
            list_editable = ["original_release"]
            fieldsets = [
                (None, {
                    "fields": ["title", "original_release"],
                }),
            ]
        site = AdminSite()
        errors = SongAdmin(Song, site).check()
        expected = [
            checks.Error(
                ("The value of 'list_editable[0]' refers to 'original_release', "
                 "which is not editable through the admin."),
                hint=None,
                obj=SongAdmin,
                id='admin.E125',
            )
        ]
        self.assertEqual(errors, expected)

    def test_editable(self):
        class SongAdmin(admin.ModelAdmin):
            list_display = ["pk", "title"]
            list_editable = ["title"]
            fieldsets = [
                (None, {
                    "fields": ["title", "original_release"],
                }),
            ]

        site = AdminSite()
        errors = SongAdmin(Song, site).check()
        self.assertEqual(errors, [])

    def test_custom_modelforms_with_fields_fieldsets(self):
        """
        # Regression test for #8027: custom ModelForms with fields/fieldsets
        """

        site = AdminSite()
        errors = ValidFields(Song, site).check()
        self.assertEqual(errors, [])

    def test_custom_get_form_with_fieldsets(self):
        """
        Ensure that the fieldsets checks are skipped when the ModelAdmin.get_form() method
        is overridden.
        Refs #19445.
        """

        site = AdminSite()
        errors = ValidFormFieldsets(Song, site).check()
        self.assertEqual(errors, [])

    def test_fieldsets_fields_non_tuple(self):
        """
        Tests for a tuple/list for the first fieldset's fields.
        """
        class NotATupleAdmin(admin.ModelAdmin):
            list_display = ["pk", "title"]
            list_editable = ["title"]
            fieldsets = [
                (None, {
                    "fields": "title"  # not a tuple
                }),
            ]

        site = AdminSite()
        errors = NotATupleAdmin(Song, site).check()
        expected = [
            checks.Error(
                "The value of 'fieldsets[0][1]['fields']' must be a list or tuple.",
                hint=None,
                obj=NotATupleAdmin,
                id='admin.E008',
            )
        ]
        self.assertEqual(errors, expected)

    def test_nonfirst_fieldset(self):
        """
        Tests for a tuple/list for the second fieldset's fields.
        """
        class NotATupleAdmin(admin.ModelAdmin):
            fieldsets = [
                (None, {
                    "fields": ("title",)
                }),
                ('foo', {
                    "fields": "author"  # not a tuple
                }),
            ]

        site = AdminSite()
        errors = NotATupleAdmin(Song, site).check()
        expected = [
            checks.Error(
                "The value of 'fieldsets[1][1]['fields']' must be a list or tuple.",
                hint=None,
                obj=NotATupleAdmin,
                id='admin.E008',
            )
        ]
        self.assertEqual(errors, expected)

    def test_exclude_values(self):
        """
        Tests for basic system checks of 'exclude' option values (#12689)
        """

        class ExcludedFields1(admin.ModelAdmin):
            exclude = 'foo'

        site = AdminSite()
        errors = ExcludedFields1(Book, site).check()
        expected = [
            checks.Error(
                "The value of 'exclude' must be a list or tuple.",
                hint=None,
                obj=ExcludedFields1,
                id='admin.E014',
            )
        ]
        self.assertEqual(errors, expected)

    def test_exclude_duplicate_values(self):
        class ExcludedFields2(admin.ModelAdmin):
            exclude = ('name', 'name')

        site = AdminSite()
        errors = ExcludedFields2(Book, site).check()
        expected = [
            checks.Error(
                "The value of 'exclude' contains duplicate field(s).",
                hint=None,
                obj=ExcludedFields2,
                id='admin.E015',
            )
        ]
        self.assertEqual(errors, expected)

    def test_exclude_in_inline(self):
        class ExcludedFieldsInline(admin.TabularInline):
            model = Song
            exclude = 'foo'

        class ExcludedFieldsAlbumAdmin(admin.ModelAdmin):
            model = Album
            inlines = [ExcludedFieldsInline]

        site = AdminSite()
        errors = ExcludedFieldsAlbumAdmin(Album, site).check()
        expected = [
            checks.Error(
                "The value of 'exclude' must be a list or tuple.",
                hint=None,
                obj=ExcludedFieldsInline,
                id='admin.E014',
            )
        ]
        self.assertEqual(errors, expected)

    def test_exclude_inline_model_admin(self):
        """
        Regression test for #9932 - exclude in InlineModelAdmin should not
        contain the ForeignKey field used in ModelAdmin.model
        """

        class SongInline(admin.StackedInline):
            model = Song
            exclude = ['album']

        class AlbumAdmin(admin.ModelAdmin):
            model = Album
            inlines = [SongInline]

        site = AdminSite()
        errors = AlbumAdmin(Album, site).check()
        expected = [
            checks.Error(
                ("Cannot exclude the field 'album', because it is the foreign key "
                 "to the parent model 'admin_checks.Album'."),
                hint=None,
                obj=SongInline,
                id='admin.E201',
            )
        ]
        self.assertEqual(errors, expected)

    def test_valid_generic_inline_model_admin(self):
        """
        Regression test for #22034 - check that generic inlines don't look for
        normal ForeignKey relations.
        """

        class InfluenceInline(GenericStackedInline):
            model = Influence

        class SongAdmin(admin.ModelAdmin):
            inlines = [InfluenceInline]

        site = AdminSite()
        errors = SongAdmin(Song, site).check()
        self.assertEqual(errors, [])

    def test_generic_inline_model_admin_non_generic_model(self):
        """
        Ensure that a model without a GenericForeignKey raises problems if it's included
        in an GenericInlineModelAdmin definition.
        """

        class BookInline(GenericStackedInline):
            model = Book

        class SongAdmin(admin.ModelAdmin):
            inlines = [BookInline]

        site = AdminSite()
        errors = SongAdmin(Song, site).check()
        expected = [
            checks.Error(
                "'admin_checks.Book' has no GenericForeignKey.",
                hint=None,
                obj=BookInline,
                id='admin.E301',
            )
        ]
        self.assertEqual(errors, expected)

    def test_generic_inline_model_admin_bad_ct_field(self):
        "A GenericInlineModelAdmin raises problems if the ct_field points to a non-existent field."

        class InfluenceInline(GenericStackedInline):
            model = Influence
            ct_field = 'nonexistent'

        class SongAdmin(admin.ModelAdmin):
            inlines = [InfluenceInline]

        site = AdminSite()
        errors = SongAdmin(Song, site).check()
        expected = [
            checks.Error(
                "'ct_field' references 'nonexistent', which is not a field on 'admin_checks.Influence'.",
                hint=None,
                obj=InfluenceInline,
                id='admin.E302',
            )
        ]
        self.assertEqual(errors, expected)

    def test_generic_inline_model_admin_bad_fk_field(self):
        "A GenericInlineModelAdmin raises problems if the ct_fk_field points to a non-existent field."

        class InfluenceInline(GenericStackedInline):
            model = Influence
            ct_fk_field = 'nonexistent'

        class SongAdmin(admin.ModelAdmin):
            inlines = [InfluenceInline]

        site = AdminSite()
        errors = SongAdmin(Song, site).check()
        expected = [
            checks.Error(
                "'ct_fk_field' references 'nonexistent', which is not a field on 'admin_checks.Influence'.",
                hint=None,
                obj=InfluenceInline,
                id='admin.E303',
            )
        ]
        self.assertEqual(errors, expected)

    def test_generic_inline_model_admin_non_gfk_ct_field(self):
        "A GenericInlineModelAdmin raises problems if the ct_field points to a field that isn't part of a GenericForeignKey"

        class InfluenceInline(GenericStackedInline):
            model = Influence
            ct_field = 'name'

        class SongAdmin(admin.ModelAdmin):
            inlines = [InfluenceInline]

        site = AdminSite()
        errors = SongAdmin(Song, site).check()
        expected = [
            checks.Error(
                "'admin_checks.Influence' has no GenericForeignKey using content type field 'name' and object ID field 'object_id'.",
                hint=None,
                obj=InfluenceInline,
                id='admin.E304',
            )
        ]
        self.assertEqual(errors, expected)

    def test_generic_inline_model_admin_non_gfk_fk_field(self):
        "A GenericInlineModelAdmin raises problems if the ct_fk_field points to a field that isn't part of a GenericForeignKey"

        class InfluenceInline(GenericStackedInline):
            model = Influence
            ct_fk_field = 'name'

        class SongAdmin(admin.ModelAdmin):
            inlines = [InfluenceInline]

        site = AdminSite()
        errors = SongAdmin(Song, site).check()
        expected = [
            checks.Error(
                "'admin_checks.Influence' has no GenericForeignKey using content type field 'content_type' and object ID field 'name'.",
                hint=None,
                obj=InfluenceInline,
                id='admin.E304',
            )
        ]
        self.assertEqual(errors, expected)

    def test_app_label_in_admin_checks(self):
        """
        Regression test for #15669 - Include app label in admin system check messages
        """

        class RawIdNonexistingAdmin(admin.ModelAdmin):
            raw_id_fields = ('nonexisting',)

        site = AdminSite()
        errors = RawIdNonexistingAdmin(Album, site).check()
        expected = [
            checks.Error(
                ("The value of 'raw_id_fields[0]' refers to 'nonexisting', which is "
                 "not an attribute of 'admin_checks.Album'."),
                hint=None,
                obj=RawIdNonexistingAdmin,
                id='admin.E002',
            )
        ]
        self.assertEqual(errors, expected)

    def test_fk_exclusion(self):
        """
        Regression test for #11709 - when testing for fk excluding (when exclude is
        given) make sure fk_name is honored or things blow up when there is more
        than one fk to the parent model.
        """

        class TwoAlbumFKAndAnEInline(admin.TabularInline):
            model = TwoAlbumFKAndAnE
            exclude = ("e",)
            fk_name = "album1"

        class MyAdmin(admin.ModelAdmin):
            inlines = [TwoAlbumFKAndAnEInline]

        site = AdminSite()
        errors = MyAdmin(Album, site).check()
        self.assertEqual(errors, [])

    def test_inline_self_check(self):
        class TwoAlbumFKAndAnEInline(admin.TabularInline):
            model = TwoAlbumFKAndAnE

        class MyAdmin(admin.ModelAdmin):
            inlines = [TwoAlbumFKAndAnEInline]

        site = AdminSite()
        errors = MyAdmin(Album, site).check()
        expected = [
            checks.Error(
                "'admin_checks.TwoAlbumFKAndAnE' has more than one ForeignKey to 'admin_checks.Album'.",
                hint=None,
                obj=TwoAlbumFKAndAnEInline,
                id='admin.E202',
            )
        ]
        self.assertEqual(errors, expected)

    def test_inline_with_specified(self):
        class TwoAlbumFKAndAnEInline(admin.TabularInline):
            model = TwoAlbumFKAndAnE
            fk_name = "album1"

        class MyAdmin(admin.ModelAdmin):
            inlines = [TwoAlbumFKAndAnEInline]

        site = AdminSite()
        errors = MyAdmin(Album, site).check()
        self.assertEqual(errors, [])

    def test_readonly(self):
        class SongAdmin(admin.ModelAdmin):
            readonly_fields = ("title",)

        site = AdminSite()
        errors = SongAdmin(Song, site).check()
        self.assertEqual(errors, [])

    def test_readonly_on_method(self):
        def my_function(obj):
            pass

        class SongAdmin(admin.ModelAdmin):
            readonly_fields = (my_function,)

        site = AdminSite()
        errors = SongAdmin(Song, site).check()
        self.assertEqual(errors, [])

    def test_readonly_on_modeladmin(self):
        class SongAdmin(admin.ModelAdmin):
            readonly_fields = ("readonly_method_on_modeladmin",)

            def readonly_method_on_modeladmin(self, obj):
                pass

        site = AdminSite()
        errors = SongAdmin(Song, site).check()
        self.assertEqual(errors, [])

    def test_readonly_dynamic_attribute_on_modeladmin(self):
        class SongAdmin(admin.ModelAdmin):
            readonly_fields = ("dynamic_method",)

            def __getattr__(self, item):
                if item == "dynamic_method":
                    def method(obj):
                        pass
                    return method
                raise AttributeError

        site = AdminSite()
        errors = SongAdmin(Song, site).check()
        self.assertEqual(errors, [])

    def test_readonly_method_on_model(self):
        class SongAdmin(admin.ModelAdmin):
            readonly_fields = ("readonly_method_on_model",)

        site = AdminSite()
        errors = SongAdmin(Song, site).check()
        self.assertEqual(errors, [])

    def test_nonexistent_field(self):
        class SongAdmin(admin.ModelAdmin):
            readonly_fields = ("title", "nonexistent")

        site = AdminSite()
        errors = SongAdmin(Song, site).check()
        expected = [
            checks.Error(
                ("The value of 'readonly_fields[1]' is not a callable, an attribute "
                 "of 'SongAdmin', or an attribute of 'admin_checks.Song'."),
                hint=None,
                obj=SongAdmin,
                id='admin.E035',
            )
        ]
        self.assertEqual(errors, expected)

    def test_nonexistent_field_on_inline(self):
        class CityInline(admin.TabularInline):
            model = City
            readonly_fields = ['i_dont_exist']  # Missing attribute

        site = AdminSite()
        errors = CityInline(State, site).check()
        expected = [
            checks.Error(
                ("The value of 'readonly_fields[0]' is not a callable, an attribute "
                 "of 'CityInline', or an attribute of 'admin_checks.City'."),
                hint=None,
                obj=CityInline,
                id='admin.E035',
            )
        ]
        self.assertEqual(errors, expected)

    def test_extra(self):
        class SongAdmin(admin.ModelAdmin):
            def awesome_song(self, instance):
                if instance.title == "Born to Run":
                    return "Best Ever!"
                return "Status unknown."

        site = AdminSite()
        errors = SongAdmin(Song, site).check()
        self.assertEqual(errors, [])

    def test_readonly_lambda(self):
        class SongAdmin(admin.ModelAdmin):
            readonly_fields = (lambda obj: "test",)

        site = AdminSite()
        errors = SongAdmin(Song, site).check()
        self.assertEqual(errors, [])

    def test_graceful_m2m_fail(self):
        """
        Regression test for #12203/#12237 - Fail more gracefully when a M2M field that
        specifies the 'through' option is included in the 'fields' or the 'fieldsets'
        ModelAdmin options.
        """

        class BookAdmin(admin.ModelAdmin):
            fields = ['authors']

        site = AdminSite()
        errors = BookAdmin(Book, site).check()
        expected = [
            checks.Error(
                ("The value of 'fields' cannot include the ManyToManyField 'authors', "
                 "because that field manually specifies a relationship model."),
                hint=None,
                obj=BookAdmin,
                id='admin.E013',
            )
        ]
        self.assertEqual(errors, expected)

    def test_cannot_include_through(self):
        class FieldsetBookAdmin(admin.ModelAdmin):
            fieldsets = (
                ('Header 1', {'fields': ('name',)}),
                ('Header 2', {'fields': ('authors',)}),
            )
        site = AdminSite()
        errors = FieldsetBookAdmin(Book, site).check()
        expected = [
            checks.Error(
                ("The value of 'fieldsets[1][1][\"fields\"]' cannot include the ManyToManyField "
                 "'authors', because that field manually specifies a relationship model."),
                hint=None,
                obj=FieldsetBookAdmin,
                id='admin.E013',
            )
        ]
        self.assertEqual(errors, expected)

    def test_nested_fields(self):
        class NestedFieldsAdmin(admin.ModelAdmin):
            fields = ('price', ('name', 'subtitle'))

        site = AdminSite()
        errors = NestedFieldsAdmin(Book, site).check()
        self.assertEqual(errors, [])

    def test_nested_fieldsets(self):
        class NestedFieldsetAdmin(admin.ModelAdmin):
            fieldsets = (
                ('Main', {'fields': ('price', ('name', 'subtitle'))}),
            )
        site = AdminSite()
        errors = NestedFieldsetAdmin(Book, site).check()
        self.assertEqual(errors, [])

    def test_explicit_through_override(self):
        """
        Regression test for #12209 -- If the explicitly provided through model
        is specified as a string, the admin should still be able use
        Model.m2m_field.through
        """

        class AuthorsInline(admin.TabularInline):
            model = Book.authors.through

        class BookAdmin(admin.ModelAdmin):
            inlines = [AuthorsInline]

        site = AdminSite()
        errors = BookAdmin(Book, site).check()
        self.assertEqual(errors, [])

    def test_non_model_fields(self):
        """
        Regression for ensuring ModelAdmin.fields can contain non-model fields
        that broke with r11737
        """

        class SongForm(forms.ModelForm):
            extra_data = forms.CharField()

        class FieldsOnFormOnlyAdmin(admin.ModelAdmin):
            form = SongForm
            fields = ['title', 'extra_data']

        site = AdminSite()
        errors = FieldsOnFormOnlyAdmin(Song, site).check()
        self.assertEqual(errors, [])

    def test_non_model_first_field(self):
        """
        Regression for ensuring ModelAdmin.field can handle first elem being a
        non-model field (test fix for UnboundLocalError introduced with r16225).
        """

        class SongForm(forms.ModelForm):
            extra_data = forms.CharField()

            class Meta:
                model = Song
                fields = '__all__'

        class FieldsOnFormOnlyAdmin(admin.ModelAdmin):
            form = SongForm
            fields = ['extra_data', 'title']

        site = AdminSite()
        errors = FieldsOnFormOnlyAdmin(Song, site).check()
        self.assertEqual(errors, [])

    def test_check_sublists_for_duplicates(self):
        class MyModelAdmin(admin.ModelAdmin):
            fields = ['state', ['state']]

        site = AdminSite()
        errors = MyModelAdmin(Song, site).check()
        expected = [
            checks.Error(
                "The value of 'fields' contains duplicate field(s).",
                hint=None,
                obj=MyModelAdmin,
                id='admin.E006'
            )
        ]
        self.assertEqual(errors, expected)

    def test_check_fieldset_sublists_for_duplicates(self):
        class MyModelAdmin(admin.ModelAdmin):
            fieldsets = [
                (None, {
                    'fields': ['title', 'album', ('title', 'album')]
                }),
            ]

        site = AdminSite()
        errors = MyModelAdmin(Song, site).check()
        expected = [
            checks.Error(
                "There are duplicate field(s) in 'fieldsets[0][1]'.",
                hint=None,
                obj=MyModelAdmin,
                id='admin.E012'
            )
        ]
        self.assertEqual(errors, expected)

    def test_list_filter_works_on_through_field_even_when_apps_not_ready(self):
        """
        Ensure list_filter can access reverse fields even when the app registry
        is not ready; refs #24146.
        """
        class BookAdminWithListFilter(admin.ModelAdmin):
            list_filter = ['authorsbooks__featured']

        # Temporarily pretending apps are not ready yet. This issue can happen
        # if the value of 'list_filter' refers to a 'through__field'.
        Book._meta.apps.ready = False
        site = AdminSite()
        try:
            errors = BookAdminWithListFilter(Book, site).check()
            self.assertEqual(errors, [])
        finally:
            Book._meta.apps.ready = True
