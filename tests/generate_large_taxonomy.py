import click
import requests


@click.command()
@click.argument('code', required=True)
@click.argument('lengths', nargs=-1, required=True, type=int)
@click.option('--url', default='https://localhost:5000/api/taxonomies/')
@click.option('--delete/--no-delete')
def generate(code, lengths, url, delete):
    if delete:
        requests.delete(f'{url}{code}/', verify=False)
    resp = requests.post(
        url,
        json={
            'code': code
        },
        verify=False
    )
    taxonomy_url = resp.json()['links']['self']
    print(taxonomy_url)

    _generate(taxonomy_url, lengths, 'node ', '.')


def _generate(url, lengths, prefix, separator):
    if not lengths:
        return
    for i in range(1, 1 + lengths[0]):
        title = f'{prefix}{i}'
        resp = requests.post(
            url,
            json={
                'title': {
                    '_': title
                },
                'slug': str(i)
            },
            verify=False
        )
        term_url = resp.json()['links']['self']
        _generate(term_url, lengths[1:], prefix + separator, separator)


if __name__ == '__main__':
    generate()
