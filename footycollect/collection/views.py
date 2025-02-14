import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import Error as DBError
from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.http import JsonResponse
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.decorators.http import require_POST
from django.views.generic import DetailView
from django.views.generic import TemplateView
from django.views.generic import View
from django.views.generic.edit import CreateView

from .forms import JerseyForm
from .forms import TestBrandForm
from .forms import TestCountryForm
from .models import Jersey
from .models import OtherItem
from .models import Outerwear
from .models import Pants
from .models import Photo
from .models import Shorts
from .models import Tracksuit

logger = logging.getLogger(__name__)


class PostCreateView(LoginRequiredMixin, View):
    template_name = "collection/item_create.html"
    form_class = JerseyForm
    success_url = reverse_lazy("collection:item_list")
    success_message = _("Item created successfully")

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        return render(request, self.template_name, {"form": form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            new_item = form.save(commit=False)
            new_item.user = request.user
            new_item.save()
            form.save_m2m()  # For many-to-many fields

            # Process uploaded files
            for file in request.FILES.getlist("images"):
                Photo.objects.create(
                    content_type=ContentType.objects.get_for_model(new_item),
                    object_id=new_item.id,
                    image=file,
                )

            messages.success(request, self.success_message)
            return JsonResponse(
                {
                    "url": reverse(
                        "collection:item_detail",
                        kwargs={"pk": new_item.pk},
                    ),
                },
            )

        return JsonResponse(
            {
                "error": form.errors.as_json(),
                "url": str(self.success_url),
            },
            status=400,
        )


@require_POST
def reorder_photos(request, item_id):
    """Handle photo reordering via AJAX."""
    try:
        new_order = request.POST.getlist("order[]")
        for index, photo_id in enumerate(new_order):
            Photo.objects.filter(id=photo_id).update(order=index)
        return JsonResponse({"status": "success"})
    except (ValidationError, DBError) as e:
        logger.exception("Error reordering photos")
        return JsonResponse({"status": "error", "message": str(e)})


def test_country_view(request):
    form = TestCountryForm()
    return render(request, "collection/test_country.html", {"form": form})


def test_brand_view(request):
    form = TestBrandForm()
    context = {"form": form}
    return render(request, "collection/test_brand.html", context)


class ItemDetailView(DetailView):
    template_name = "collection/item_detail.html"

    def get_queryset(self):
        """Return queryset based on item type"""
        model_map = {
            "jersey": Jersey,
            "shorts": Shorts,
            "outerwear": Outerwear,
            "tracksuit": Tracksuit,
            "pants": Pants,
            "other": OtherItem,
        }
        # Get item type from URL or session
        item_type = self.kwargs.get("item_type", "jersey")
        return model_map[item_type].objects.all()


def home(request):
    photos = Photo.objects.all()
    context = {
        "photos": photos,
    }
    return render(request, "collection/item_create.html", context)


@csrf_exempt
def file_upload(request):
    if request.method == "POST":
        my_file = request.FILES.get("file")
        Photo.objects.create(image=my_file)
        return HttpResponse("")
    return JsonResponse({"post": "false"})


def test_dropzone(request):
    """Independent test view for Dropzone"""
    return render(request, "collection/dropzone_test_page.html")


class DropzoneTestView(TemplateView):
    template_name = "collection/dropzone_test_page.html"


@require_http_methods(["POST", "DELETE"])
def handle_dropzone_files(request):
    """Handles file upload and deletion for Dropzone"""
    if request.method == "POST":
        # Create a test file without associating it with a model
        file = request.FILES.get("file")
        if not file:
            return HttpResponseBadRequest(_("No file provided"))

        # Simulate saving (in reality we don't save)
        file_data = {
            "name": file.name,
            "size": file.size,
            "url": "#",
            "deleteUrl": reverse("collection:handle_dropzone_files"),
            "deleteType": "DELETE",
        }
        return JsonResponse(file_data)

    if request.method == "DELETE":
        # Simulate deletion
        file_name = request.POST.get("fileName")
        return JsonResponse(
            {"success": True, "message": _("File {} deleted").format(file_name)},
        )

    return HttpResponseBadRequest(_("Method not allowed"))


class ItemCreateView(LoginRequiredMixin, CreateView):
    model = Jersey
    form_class = JerseyForm
    template_name = "collection/item_create.html"

    def get_success_url(self):
        return reverse_lazy("collection:item_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        try:
            self.object = form.save(commit=False)
            self.object.user = self.request.user
            self.object.save()
            form.save_m2m()

            # Get the IDs and order of the photos
            photo_data = json.loads(self.request.POST.get("photo_ids", "[]"))
            logger.info("Photo data received: %s", photo_data)

            if photo_data:
                photos = Photo.objects.filter(
                    id__in=[p["id"] for p in photo_data],
                    user=self.request.user,
                ).select_related("content_type")

                content_type = ContentType.objects.get_for_model(self.object)
                update_batch = []

                for photo in photos:
                    photo.content_type = content_type
                    photo.object_id = self.object.id
                    photo.order = next(
                        p["order"] for p in photo_data if p["id"] == photo.id
                    )
                    photo.user = None
                    update_batch.append(photo)

                Photo.objects.bulk_update(
                    update_batch,
                    ["content_type", "object_id", "order", "user"],
                )

            messages.success(self.request, _("Item created successfully!"))
            return redirect(self.get_success_url())

        except (ValidationError, DBError) as e:
            logger.exception("Error creating item")
            messages.error(self.request, _("Error: {}").format(str(e)))
            return self.form_invalid(form)
        except OSError:  # For I/O errors
            logger.exception("System error")
            messages.error(self.request, _("System error"))
            return self.form_invalid(form)

    def form_invalid(self, form):
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, _("{}: {}").format(field, error))
        return super().form_invalid(form)


@login_required
@require_POST
def upload_photo(request):
    try:
        file = request.FILES.get("photo")
        if not file:
            return JsonResponse({"error": _("No file received")}, status=400)

        # Server validations
        if file.size > 15 * 1024 * 1024:
            return JsonResponse({"error": _("The file exceeds 15MB")}, status=413)

        if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
            return JsonResponse({"error": _("File type not supported")}, status=415)

        # Create a photo without associating it with any item yet
        photo = Photo.objects.create(
            image=file,
            order=request.POST.get("order", 0),
            # Temporarily save the user_id to be able to clean orphan photos later
            user=request.user,
        )

        return JsonResponse(
            {
                "id": photo.id,
                "url": photo.get_image_url(),
                "thumbnail_url": photo.thumbnail.url if photo.thumbnail else None,
            },
        )

    except (ValidationError, DBError) as e:
        logger.exception("Error creating photo")
        messages.error(request, _("Error: {}").format(str(e)))
        return JsonResponse({"error": str(e)}, status=500)
    except OSError:  # For I/O errors
        logger.exception("System error")
        messages.error(request, _("System error"))
        return JsonResponse({"error": _("System error")}, status=500)
