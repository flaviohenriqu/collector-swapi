import asyncio
from functools import lru_cache
from uuid import UUID, uuid4

import aiohttp
import petl as etl
import requests
from dateutil.parser import parse
from django.conf import settings
from django.core.paginator import EmptyPage, Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ColumnsForm
from .models import Collection


async def _fetch(session: aiohttp.ClientSession, url: str):
    """
    Asynchronously fetches data from the specified URL using the provided session object.

    Args:
        session: aiohttp.ClientSession: Session object to use for making the request.
        url: str: URL to fetch data from.

    Returns:
        dict: JSON data retrieved from the URL.
    """
    async with session.get(url) as response:
        return await response.json()


@lru_cache
def get_planet_name(url: str) -> str:
    """
    Retrieves the name of a planet from the specified URL using an LRU cache to store results.

    Args:
        url: str: URL of the planet to retrieve the name of.

    Returns:
        str: Name of the planet.
    """
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data.get("name")
    else:
        return ""


@lru_cache
def get_date(edited: str) -> str:
    """
    Parses a date string and returns it in the format 'YYYY-MM-DD' using an LRU cache to store results.

    Args:
        edited: str: Date string to parse.

    Returns:
        str: Parsed date string in the format 'YYYY-MM-DD'.
    """
    return parse(edited).strftime("%Y-%m-%d")


def index(request):
    """
    Renders the index page for the Swapi app.

    Args:
        request: django.http.HttpRequest: Request object representing the current HTTP request.

    Returns:
        django.shortcuts.render: Rendered index template.
    """
    collections = Collection.objects.order_by("-created_at")
    return render(request, "swapi/index.html", {"collections": collections})


async def create_collection(request):
    """
    Asynchronously creates a new collection of data from the SWAPI API and saves it to a CSV file.

    Args:
        request: django.http.HttpRequest: Request object representing the current HTTP request.

    Returns:
        django.shortcuts.redirect: Redirect to the index page after the collection has been created.
    """
    data = []
    uid = uuid4()
    filename = f"{uid}.csv"
    url = f"{settings.SWAPI_BASE_URL}/people/"
    async with aiohttp.ClientSession() as session:
        while url:
            results = await _fetch(session, url)
            data.extend(results["results"])
            url = results["next"]
    tbl = etl.fromdicts(
        data,
        header=[
            "name",
            "height",
            "mass",
            "hair_color",
            "skin_color",
            "eye_color",
            "birth_year",
            "gender",
            "homeworld",
            "edited",
        ],
    )
    tbl = etl.addfield(
        tbl, "homeworld_name", lambda rec: get_planet_name(rec["homeworld"])
    )
    tbl = etl.addfield(tbl, "date", lambda rec: get_date(rec["edited"]))
    tbl = etl.cut(
        tbl,
        "name",
        "height",
        "mass",
        "hair_color",
        "skin_color",
        "eye_color",
        "birth_year",
        "gender",
        "homeworld_name",
        "date",
    )
    tbl = etl.rename(tbl, "homeworld_name", "homeworld")
    etl.tocsv(tbl, f"{settings.COLLECTIONS_BASE}/{filename}")

    collection = Collection()
    collection.uid = uid
    collection.file.name = filename
    await collection.asave()

    return redirect("swapi:index")


def _get_data(collection_uid: UUID):
    """
    Given a UUID identifying a Collection object, returns a tuple containing the ETL table
    created from the CSV file associated with the Collection, and the Collection object itself.

    Args:
        collection_uid: UUID of the Collection object

    Returns:
        tuple: A tuple containing the ETL table created from the CSV file associated with the
        Collection object identified by collection_uid, and the Collection object itself.

    Raises:
        Http404: If the Collection object identified by collection_uid does not exist.
    """
    collection = get_object_or_404(Collection, pk=collection_uid)
    table = etl.fromcsv(f"{settings.COLLECTIONS_BASE}/{collection.file.url}")

    return table, collection


def list_csv(request, collection_uid: UUID):
    """
    Given an HTTP request object and a UUID identifying a Collection object, returns a response
    object containing a paginated JSON or HTML representation of the ETL table created from the
    CSV file associated with the Collection.

    Args:
        request: An HTTP request object
        collection_uid: UUID of the Collection object

    Returns:
        HttpResponse: An HTTP response object containing a paginated JSON or HTML representation
        of the ETL table created from the CSV file associated with the Collection.

    Raises:
        Http404: If the Collection object identified by collection_uid does not exist.
    """
    is_ajax = request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"
    table, collection = _get_data(collection_uid)

    page_number = request.GET.get("page", 1)

    rows_per_page = 10
    start_row = (int(page_number) - 1) * rows_per_page
    end_row = start_row + rows_per_page

    rows = etl.rowslice(table.skip(1), 0, end_row - 1)

    data = list(rows)

    has_more_pages = len(table) > end_row

    context = {
        "rows": data,
        "headers": etl.header(table),
        "collection": collection,
        "has_more": has_more_pages,
    }
    if is_ajax:
        return JsonResponse({"rows": data, "has_more": has_more_pages})
    else:
        return render(request, "swapi/list.html", context=context)


def value_count(request, collection_uid: UUID):
    """
    View function for displaying a value count of selected columns from a CSV file in a collection.

    Args:
        request (HttpRequest): The request object sent by the client.
        collection_uid (UUID): The unique identifier of the collection to get the CSV file from.

    Returns:
        HttpResponse: The HTTP response with a rendered HTML template displaying the value count.

    Raises:
        Http404: If the collection with the given UID does not exist.

    Example:
        To get a value count of the "birth_year" and "homeworld" columns from a collection with UID "d4b93ab4-95fc-4cd2-a2c5-e464f5a36e53",
        make a GET request to "/value-count/d4b93ab4-95fc-4cd2-a2c5-e464f5a36e53" and the result will be displayed as an HTML page.

        To get a value count of other columns, make a POST request to the same URL with a form containing a checkbox for each desired column.
    """
    table, collection = _get_data(collection_uid)
    columns = ["birth_year", "homeworld"]

    form = ColumnsForm(request.POST or None)
    if form.is_valid():
        columns = form.cleaned_data.get("columns")

    agg = etl.aggregate(table, key=columns, aggregation=len).sort("value", reverse=True)

    context = {
        "form": form,
        "collection": collection,
        "rows": agg.skip(1),
        "headers": etl.header(agg),
    }
    return render(request, "swapi/value_count.html", context=context)
