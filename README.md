# Flask Taxonomies

[![](https://img.shields.io/github/license/oarepo/flask-taxonomies.svg)](https://github.com/oarepo/flask-taxonomies/blob/master/LICENSE)
[![](https://img.shields.io/travis/oarepo/flask-taxonomies.svg)](https://travis-ci.org/oarepo/flask-taxonomies)
[![](https://img.shields.io/coveralls/oarepo/flask-taxonomies.svg)](https://coveralls.io/r/oarepo/flask-taxonomies)
[![](https://img.shields.io/pypi/v/flask-taxonomies.svg)](https://pypi.org/pypi/flask-taxonomies)

## Installation

```bash
pip install flask-taxonomies
```

```python
from flask_taxonomies.ext import FlaskTaxonomies
from flask_taxonomies.views import blueprint
from flask import Flask

app = Flask('__test__')

FlaskTaxonomies(app)
app.register_blueprint(blueprint, url_prefix=app.config['FLASK_TAXONOMIES_URL_PREFIX'])

db = ...
from flask_taxonomies.models import Base
Base.metadata.create_all(db.engine)
```

## Principles

**Taxonomy** is a tree of taxonomy terms. It is represented as a database object identified by
*code*. A taxonomy may contain its original url (in case the taxonomy is defined elsewhere)
and additional metadata as a json object (containing, for example, taxonomy title).

**TaxonomyTerm** represents a single node in a taxonomy. It is identified by its *slug* 
and may contain additional metadata as json object. A term can contain children to represent
hierarchy of taxonomy terms. Term does not define ordering within children, it is up to 
application logic to define any ordering.   

## REST API

The rest API sits on the ``app.config['FLASK_TAXONOMIES_URL_PREFIX']`` url, implicitly 
``/api/2.0/taxonomies/``. It follows the REST API principles with pagination inspired
by GitHub API. 

### Resource representation

Implicitly, the API returns rather minimal representation. The amount of the returned metadata
can be changed via HTTP ``prefer`` header or alternatively by query parameters.

#### Prefer header

##### Return representation

See [rfc7240](https://tools.ietf.org/html/rfc7240) for introduction to prefer header.

If the header is not present, ``return=representation`` is assumed. One can specify ``return=minimal``
to obtain minimal dataset, or other return types defined in ``FLASK_TAXONOMIES_REPRESENTATION`` config.

**return=minimal**

returns the minimal representation. Mostly not usable directly as it does not return any metadata,
just the code and slug

*Listing:*
```
$ curl -i -H "Prefer: return=minimal" http://127.0.0.1:5000/api/2.0/taxonomies/
HTTP/1.0 200 OK
X-Page: 1
X-PageSize: None
X-Total: None
Link: <http://127.0.0.1:5000/api/2.0/taxonomies/>; rel=self
Content-Length: 34
Server: Werkzeug/1.0.1 Python/3.8.2
Date: Sun, 28 Jun 2020 17:30:45 GMT

[
  {
    "code": "country"
  }
]
```

*Get taxonomy:*
```
$ curl -i -H "Prefer: return=minimal" http://127.0.0.1:5000/api/2.0/taxonomies/country
HTTP/1.0 200 OK
Content-Type: application/json
Content-Length: 24
Server: Werkzeug/1.0.1 Python/3.8.2
Date: Sun, 28 Jun 2020 17:40:43 GMT

{
  "code": "country"
}
```

*Get term:*
```
$ curl -i -H "Prefer: return=minimal" http://127.0.0.1:5000/api/2.0/taxonomies/country/europe
HTTP/1.0 200 OK
Link: <https://localhost/api/2.0/taxonomies/country/europe>; rel=self, <https://localhost/api/2.0/taxonomies/country/europe?representation:include=dsc>; rel=tree
Content-Length: 23
Server: Werkzeug/1.0.1 Python/3.8.2
Date: Sun, 28 Jun 2020 20:01:37 GMT

{
  "slug": "europe"
}
```

**return=representation**

this is the default return type. Returns all the metadata declared on taxonomy/term. For example:

*Listing:*
```
$ curl -i http://127.0.0.1:5000/api/2.0/taxonomies/
HTTP/1.0 200 OK
Link: <http://127.0.0.1:5000/api/2.0/taxonomies/>; rel=self
Content-Length: 69
Server: Werkzeug/1.0.1 Python/3.8.2
Date: Sun, 28 Jun 2020 20:05:01 GMT

[
  {
    "code": "country", 
    "title": "List of countries"
  }
]
```

*Get term:*
```
$ curl -i http://127.0.0.1:5000/api/2.0/taxonomies/country/europe/cz
HTTP/1.0 200 OK
Link: <https://localhost/api/2.0/taxonomies/country/europe/cz>; rel=self, <https://localhost/api/2.0/taxonomies/country/europe/cz?representation:include=dsc>; rel=tree
Content-Length: 200
Server: Werkzeug/1.0.1 Python/3.8.2
Date: Sun, 28 Jun 2020 20:19:57 GMT

{
  "CapitalLatitude": "50.083333333333336", 
  "CapitalLongitude": "14.466667", 
  "CapitalName": "Prague", 
  "ContinentName": "Europe", 
  "CountryCode": "CZ", 
  "CountryName": "Czech Republic"
}

```

##### Includes and excludes

The returned representation can be modified by specifying which metadata should be included/excluded. 
Currently supported includes/excludes are:

```python
INCLUDE_URL = 'url'
INCLUDE_DESCENDANTS_URL = 'drl'
INCLUDE_ANCESTORS = 'anc'
INCLUDE_DATA = 'data'
INCLUDE_ID = 'id'
INCLUDE_DESCENDANTS = 'dsc'
INCLUDE_ENVELOPE='env'
INCLUDE_DELETED = 'del'
INCLUDE_SLUG = 'slug'
INCLUDE_LEVEL = 'lvl'
```

Examples:

**Include record url**

```
GET /api/2.0/taxonomies/country
Prefer: return=representation; include=url

HTTP 1.1 200 OK
Link: <.../api/2.0/taxonomies/country> rel=self

{
  "title": "Taxonomy of countries",
  "links": {
    "self": ".../api/2.0/taxonomies/country"
  }
}
```

**Include descendants url**

```
GET /api/2.0/taxonomies/country
Prefer: return=representation; include=url drl

HTTP 1.1 200 OK
Link: <.../api/2.0/taxonomies/country> rel=self

{
  "title": "Taxonomy of countries",
  "links": {
    "self": ".../api/2.0/taxonomies/country",
    "tree": ".../api/2.0/taxonomies/country?representation:include=drl",
  }
}
```

#### Query parameters


## Python API 

## Configuration