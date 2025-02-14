# Create your views here.

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic.edit import CreateView
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST, require_http_methods
from django.core.files.storage import FileSystemStorage
from django.contrib.contenttypes.models import ContentType
from django.views.generic import DetailView
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.core.files.base import ContentFile
from django.views.generic import View

from django.views.generic import TemplateView
from django.utils.translation import gettext as _

from .forms import (
    BaseItemForm,
    ItemTypeForm,
    JerseyForm,
    OuterwearForm,
    ShortsForm,
    TrackSuitForm,
    PantsForm,
    OtherItemForm,
    ItemPhotosForm,
    TestCountryForm,
    TestBrandForm,
)
from .models import Photo, Jersey, Shorts, Outerwear, Tracksuit, Pants, OtherItem
import json


class PostCreateView(LoginRequiredMixin, View):
    template_name = 'collection/item_create.html'
    form_class = JerseyForm
    success_url = reverse_lazy('collection:item_list')
    success_message = _('Item created successfully')

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            new_item = form.save(commit=False)
            new_item.user = request.user
            new_item.save()
            form.save_m2m()  # For many-to-many fields
            
            # Process uploaded files
            for file in request.FILES.getlist('images'):
                Photo.objects.create(
                    content_type=ContentType.objects.get_for_model(new_item),
                    object_id=new_item.id,
                    image=file
                )
            
            messages.success(request, self.success_message)
            return JsonResponse({
                'url': reverse('collection:item_detail', kwargs={'pk': new_item.pk})
            })
        
        return JsonResponse({
            'error': form.errors.as_json(),
            'url': str(self.success_url)
        }, status=400)

@require_POST
def reorder_photos(request, item_id):
    """Handle photo reordering via AJAX."""
    try:
        new_order = request.POST.getlist('order[]')
        for index, photo_id in enumerate(new_order):
            Photo.objects.filter(id=photo_id).update(order=index)
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

def test_country_view(request):
    form = TestCountryForm()
    return render(request, 'collection/test_country.html', {'form': form})

def test_brand_view(request):
    form = TestBrandForm()
    context = {'form': form}
    return render(request, 'collection/test_brand.html', context)

class ItemDetailView(DetailView):
    template_name = 'collection/item_detail.html'
    
    def get_queryset(self):
        """Return queryset based on item type"""
        model_map = {
            'jersey': Jersey,
            'shorts': Shorts,
            'outerwear': Outerwear,
            'tracksuit': Tracksuit,
            'pants': Pants,
            'other': OtherItem,
        }
        # Get item type from URL or session
        item_type = self.kwargs.get('item_type', 'jersey')
        return model_map[item_type].objects.all()

def home(request):
    photos = Photo.objects.all()
    context = {
        'photos': photos
    }
    return render(request, 'collection/item_create.html', context)

@csrf_exempt 
def file_upload(request):
    if request.method == 'POST':
        my_file = request.FILES.get('file')
        Photo.objects.create(image=my_file)
        return HttpResponse('')
    return JsonResponse({'post': 'false'})

def test_dropzone(request):
    """Vista de prueba independiente para Dropzone"""
    return render(request, 'collection/dropzone_test_page.html')

class DropzoneTestView(TemplateView):
    template_name = 'collection/dropzone_test_page.html'

@require_http_methods(["POST", "DELETE"])
def handle_dropzone_files(request):
    """Maneja subida y eliminación de archivos para Dropzone"""
    if request.method == "POST":
        # Crear archivo de prueba sin asociar a modelo
        file = request.FILES.get('file')
        if not file:
            return HttpResponseBadRequest("No file provided")
        
        # Simular guardado (en realidad no guardamos)
        file_data = {
            'name': file.name,
            'size': file.size,
            'url': '#',  
            'deleteUrl': reverse('collection:handle_dropzone_files'),
            'deleteType': "DELETE",
        }
        return JsonResponse(file_data)
    
    elif request.method == "DELETE":
        # Simular eliminación
        file_name = request.POST.get('fileName')
        return JsonResponse({'success': True, 'message': f'Archivo {file_name} eliminado'})

    return HttpResponseBadRequest("Método no permitido")

class ItemCreateView(LoginRequiredMixin, CreateView):
    model = Jersey
    form_class = JerseyForm
    template_name = 'collection/item_create.html'
    
    def get_success_url(self):
        return reverse_lazy('collection:item_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        try:
            # Guardar el item
            self.object = form.save(commit=False)
            self.object.user = self.request.user
            self.object.save()
            form.save_m2m()

            # Procesar fotos
            files = self.request.FILES.getlist('photos')
            print(f"Archivos recibidos: {len(files)}")
            
            for idx, photo_file in enumerate(files):
                print(f"Procesando foto {idx + 1}: {photo_file.name}")
                Photo.objects.create(
                    content_object=self.object,
                    image=photo_file,
                    order=idx
                )

            # Construir URL absoluta
            success_url = self.get_success_url()
            if not success_url.startswith('/'):
                success_url = '/' + success_url
                
            print(f"Redirigiendo a: {success_url}")
            
            return JsonResponse({
                'url': success_url
            })

        except Exception as e:
            print(f"Error al crear item: {str(e)}")
            return JsonResponse({
                'error': str(e)
            }, status=400)

    def form_invalid(self, form):
        print("Formulario inválido:", form.errors)
        return JsonResponse({
            'error': form.errors
        }, status=400)
