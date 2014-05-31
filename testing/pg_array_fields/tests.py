# -*- coding: utf-8 -*-

import datetime

import django
from django.contrib.admin import AdminSite, ModelAdmin
from django.core.serializers import serialize, deserialize
from django.db import connection
from django import forms
from django.test import TestCase
from django.utils.encoding import force_text

from djorm_pgarray.fields import ArrayField, ArrayFormField

from .forms import IntArrayForm
from .models import (IntModel,
                     TextModel,
                     DoubleModel,
                     MTextModel,
                     MultiTypeModel,
                     ChoicesModel,
                     Item,
                     Item2,
                     DateModel,
                     DateTimeModel,
                     MacAddrModel)

import psycopg2.extensions

# Adapters

class MacAddr(str):
    pass


def custom_type_cast(val):
    return val


def get_type_oid(sql_expression):
    """Query the database for the OID of the type of sql_expression."""
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT " + sql_expression)
        return cursor.description[0][1]
    finally:
        cursor.close()

def cast_macaddr(val, cur):
    return MacAddr(val)


def adapt_macaddr(maddr):
    from psycopg2.extensions import adapt, AsIs
    return AsIs("{0}::macaddr".format(adapt(str(maddr))))


def register_macaddr_type():
    from psycopg2.extensions import register_adapter, new_type, register_type, new_array_type
    import psycopg2

    oid = get_type_oid("NULL::macaddr")
    PGTYPE = new_type((oid,), "macaddr", cast_macaddr)
    register_type(PGTYPE)
    register_adapter(MacAddr, adapt_macaddr)

    mac_array_oid = get_type_oid("'{}'::macaddr[]")
    array_of_mac = new_array_type((mac_array_oid, ), 'macaddr', psycopg2.STRING)
    psycopg2.extensions.register_type(array_of_mac)


# Tests

class ArrayFieldTests(TestCase):
    def setUp(self):
        IntModel.objects.all().delete()
        TextModel.objects.all().delete()
        DoubleModel.objects.all().delete()
        MultiTypeModel.objects.all().delete()

    def test_default_value_1(self):
        """Test default value on model is created."""
        obj = Item.objects.create()
        self.assertEqual(obj.tags, [])

        obj = Item2.objects.create()
        self.assertEqual(obj.tags, [])

    def test_date(self):
        """Test date array fields."""
        d = datetime.date(2011, 11, 11)
        instance = DateModel.objects.create(dates=[d])

        instance = DateModel.objects.get(pk=instance.pk)
        self.assertEqual(instance.dates[0], d)

    def test_datetime(self):
        d = datetime.datetime(2011, 11, 11, 11, 11, 11)
        instance = DateTimeModel.objects.create(dates=[d])
        instance = DateTimeModel.objects.get(pk=instance.pk)
        self.assertEqual(instance.dates[0], d)

    def test_empty_create(self):
        instance = IntModel.objects.create(lista=[])
        instance = IntModel.objects.get(pk=instance.pk)
        self.assertEqual(instance.lista, [])

    def test_macaddr_model(self):
        register_macaddr_type()
        instance = MacAddrModel.objects.create()
        instance.lista = [MacAddr('00:24:d6:54:ff:c6'), MacAddr('00:24:d6:54:ff:c4')]
        instance.save()

        instance = MacAddrModel.objects.get(pk=instance.pk)
        self.assertEqual(instance.lista, ['00:24:d6:54:ff:c6', '00:24:d6:54:ff:c4'])

    def test_correct_behavior_with_text_arrays_01(self):
        obj = TextModel.objects.create(lista=[[1,2],[3,4]])
        obj = TextModel.objects.get(pk=obj.pk)
        self.assertEqual(obj.lista, [[u'1', u'2'], [u'3', u'4']])

    def test_correct_behavior_with_text_arrays_02(self):
        obj = MTextModel.objects.create(data=[[u"1",u"2"],[u"3",u"ñ"]])
        obj = MTextModel.objects.get(pk=obj.pk)
        self.assertEqual(obj.data, [[u"1",u"2"],[u"3",u"ñ"]])

    def test_correct_behavior_with_int_arrays(self):
        obj = IntModel.objects.create(lista=[1,2,3])
        obj = IntModel.objects.get(pk=obj.pk)
        self.assertEqual(obj.lista, [1, 2, 3])

    def test_correct_behavior_with_float_arrays(self):
        obj = DoubleModel.objects.create(lista=[1.2,2.4,3])
        obj = DoubleModel.objects.get(pk=obj.pk)
        self.assertEqual(obj.lista, [1.2, 2.4, 3])

    def test_value_to_string_serializes_correctly(self):
        obj = MTextModel.objects.create(data=[[u"1",u"2"],[u"3",u"ñ"]])
        obj_int = IntModel.objects.create(lista=[1,2,3])

        serialized_obj = serialize('json', MTextModel.objects.filter(pk=obj.pk))
        serialized_obj_int = serialize('json', IntModel.objects.filter(pk=obj_int.pk))

        obj.delete()
        obj_int.delete()

        deserialized_obj = list(deserialize('json', serialized_obj))[0]
        deserialized_obj_int = list(deserialize('json', serialized_obj_int))[0]

        obj = deserialized_obj.object
        obj_int = deserialized_obj_int.object
        obj.save()
        obj_int.save()

        self.assertEqual(obj.data, [[u"1",u"2"],[u"3",u"ñ"]])
        self.assertEqual(obj_int.lista, [1,2,3])

    def test_to_python_serializes_xml_correctly(self):
        obj = MTextModel.objects.create(data=[[u"1",u"2"],[u"3",u"ñ"]])
        obj_int = IntModel.objects.create(lista=[1,2,3])

        serialized_obj = serialize('xml', MTextModel.objects.filter(pk=obj.pk))
        serialized_obj_int = serialize('xml', IntModel.objects.filter(pk=obj_int.pk))

        obj.delete()
        obj_int.delete()
        deserialized_obj = list(deserialize('xml', serialized_obj))[0]
        deserialized_obj_int = list(deserialize('xml', serialized_obj_int))[0]
        obj = deserialized_obj.object
        obj_int = deserialized_obj_int.object
        obj.save()
        obj_int.save()

        self.assertEqual(obj.data, [[u"1",u"2"],[u"3",u"ñ"]])
        self.assertEqual(obj_int.lista, [1,2,3])

    def test_can_override_formfield(self):
        model_field = ArrayField()
        class FakeFieldClass(object):
            def __init__(self, *args, **kwargs):
                pass
        form_field = model_field.formfield(form_class=FakeFieldClass)
        self.assertIsInstance(form_field, FakeFieldClass)

    def test_default_formfield_with_choices(self):
        model_field = ArrayField(choices=[('a', 'a')], dbtype='text')
        form_field = model_field.formfield()
        self.assertIsInstance(form_field, forms.TypedMultipleChoiceField)
        self.assertEqual(form_field.choices, [('a', 'a')])
        self.assertEqual(form_field.coerce, force_text)

    def test_other_types_properly_casted(self):
        obj = MultiTypeModel.objects.create(
            smallints=[1, 2, 3],
            varchars=['One', 'Two', 'Three']
        )
        obj = MultiTypeModel.objects.get(pk=obj.pk)

        self.assertEqual(obj.smallints, [1, 2, 3])
        self.assertEqual(obj.varchars, ['One', 'Two', 'Three'])

    def test_choices_validation(self):
        obj = ChoicesModel(choices=['A'])
        obj.full_clean()
        obj.save()


if django.VERSION[:2] >= (1, 7):
    class ArrayLookupsFieldTests(TestCase):
        def setUp(self):
            IntModel.objects.all().delete()

        def test_contains_lookup(self):
            obj1 = IntModel.objects.create(lista=[1,4,3])
            obj2 = IntModel.objects.create(lista=[0,10,50])

            qs = IntModel.objects.filter(lista__contains=[1,3])
            self.assertEqual(qs.count(), 1)

        def test_contained_by_lookup(self):
            obj1 = IntModel.objects.create(lista=[2,7])
            obj2 = IntModel.objects.create(lista=[0,10,50])

            qs = IntModel.objects.filter(lista__contained_by=[1,7,4,2,6])
            self.assertEqual(qs.count(), 1)

        def test_overlap_lookup(self):
            obj1 = IntModel.objects.create(lista=[1,4,3])
            obj2 = IntModel.objects.create(lista=[0,10,50])

            qs = IntModel.objects.filter(lista__overlap=[2,1])
            self.assertEqual(qs.count(), 1)

        def test_contains_unicode(self):
            obj = TextModel.objects.create(lista=[u"Fóö", u"Пример", u"test"])
            qs = TextModel.objects.filter(lista__contains=[u"Пример"])
            self.assertEqual(qs.count(), 1)

        def test_deconstruct_defaults(self):
            """Attributes at default values left out of deconstruction."""
            af = ArrayField()

            name, path, args, kwargs = af.deconstruct()

            naf = ArrayField(*args, **kwargs)

            self.assertEqual((args, kwargs), ([], {}))
            self.assertEqual(af._array_type, naf._array_type)
            self.assertEqual(af._dimension, naf._dimension)
            self.assertEqual(af._type_cast, naf._type_cast)
            self.assertEqual(af.blank, naf.blank)
            self.assertEqual(af.null, naf.null)
            self.assertEqual(af.default, naf.default)

        def test_deconstruct_custom(self):
            """Attributes at custom values included in deconstruction."""
            af = ArrayField(
                dbtype='text',
                dimension=2,
                type_cast=custom_type_cast,
                blank=False,
                null=False,
                default=[['a'], ['b']],
            )

            name, path, args, kwargs = af.deconstruct()

            naf = ArrayField(*args, **kwargs)

            self.assertEqual(args, [])
            self.assertEqual(
                kwargs,
                {
                    'dbtype': 'text',
                    'dimension': 2,
                    'type_cast': custom_type_cast,
                    'blank': False,
                    'null': False,
                    'default': [['a'], ['b']],
                },
            )
            self.assertEqual(af._array_type, naf._array_type)
            self.assertEqual(af._dimension, naf._dimension)
            self.assertEqual(af._type_cast, naf._type_cast)
            self.assertEqual(af.blank, naf.blank)
            self.assertEqual(af.null, naf.null)
            self.assertEqual(af.default, naf.default)

        def test_deconstruct_unknown_dbtype(self):
            """Deconstruction does not include type_cast if dbtype unknown."""
            af = ArrayField(dbtype='foo')

            name, path, args, kwargs = af.deconstruct()

            naf = ArrayField(*args, **kwargs)

            self.assertEqual(kwargs, {'dbtype': 'foo'})


class ArrayFormFieldTests(TestCase):
    def test_regular_forms(self):
        form = IntArrayForm()
        self.assertFalse(form.is_valid())
        form = IntArrayForm({'lista':u'1,2'})
        self.assertTrue(form.is_valid())

    def test_empty_value(self):
        form = IntArrayForm({'lista':u''})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['lista'], [])

    def test_admin_forms(self):
        site = AdminSite()
        model_admin = ModelAdmin(IntModel, site)
        form_clazz = model_admin.get_form(None)
        form_instance = form_clazz()

        try:
            form_instance.as_table()
        except TypeError:
            self.fail('HTML Rendering of the form caused a TypeError')

    def test_unicode_data(self):
        field = ArrayFormField()
        result = field.prepare_value([u"Клиент",u"こんにちは"])
        self.assertEqual(result, u"Клиент,こんにちは")

    def test_invalid_error(self):
        form = IntArrayForm({'lista':1})
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['lista'],
            [u'Enter a list of values, joined by commas.  E.g. "a,b,c".']
            )
