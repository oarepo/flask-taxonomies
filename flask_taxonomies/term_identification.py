from flask_taxonomies.models import Taxonomy, TaxonomyError, TaxonomyTerm


class TermIdentification:
    def __init__(self, taxonomy=None, parent=None, slug=None, term=None):
        if term:
            if parent:
                raise TaxonomyError('`parent` should not be used when `term` is specified')
            if taxonomy:
                raise TaxonomyError('`taxonomy` should not be used when `term` is specified')
            if slug:
                raise TaxonomyError('`slug` should not be used when `term` is specified')
        elif parent:
            if not slug:
                raise TaxonomyError('`slug` must be used when `parent` is specified')
            if taxonomy:
                raise TaxonomyError('`taxonomy` must not be used when `parent` is specified')
        elif taxonomy:
            if not slug:
                raise TaxonomyError('`slug` must be used when `taxonomy` is specified')
        else:
            if not slug or '/' not in slug:
                raise TaxonomyError(
                    '`slug` including taxonomy code must be used when no other parameters are specified')

        if not term:
            if not parent:
                if taxonomy is None:
                    taxonomy, slug = slug.split('/', maxsplit=1)
            elif isinstance(parent, str):
                slug = parent + '/' + slug
                taxonomy, slug = slug.split('/', maxsplit=1)
            else:
                slug = parent.slug + '/' + slug
                taxonomy = parent.taxonomy_id

        self.term = term
        self.taxonomy = taxonomy
        self.slug = slug

    def _filter_taxonomy(self, query):
        if isinstance(self.taxonomy, Taxonomy):
            return query.filter(TaxonomyTerm.taxonomy_id == self.taxonomy.id)
        elif isinstance(self.taxonomy, str):
            return query.join(Taxonomy).filter(Taxonomy.code == self.taxonomy)
        else:
            return query.filter(TaxonomyTerm.taxonomy_id == self.taxonomy)

    def parent_identification(self):
        if self.term:
            if not self.term.parent_id:
                return None
            return TermIdentification(term=self.term.parent)
        if '/' not in self.slug:
            return None
        return TermIdentification(taxonomy=self.taxonomy, slug='/'.join(self.slug.split('/')[:-1]))

    def term_query(self, session):
        ret = session.query(TaxonomyTerm)
        if self.term:
            return ret.filter(TaxonomyTerm.id == self.term.id)
        ret = self._filter_taxonomy(ret)
        if self.slug:
            ret = ret.filter(TaxonomyTerm.slug == self.slug)
        return ret

    def descendant_query(self, session):
        ret = session.query(TaxonomyTerm)
        if self.term:
            return ret.filter(
                TaxonomyTerm.taxonomy_id == self.term.taxonomy_id,
                TaxonomyTerm.slug.descendant_of(self.term.slug),
            )
        ret = self._filter_taxonomy(ret)
        if self.slug:
            ret = ret.filter(TaxonomyTerm.slug.descendant_of(self.slug))
        return ret

    def ancestor_query(self, session):
        ret = session.query(TaxonomyTerm)
        if self.term:
            return ret.filter(
                TaxonomyTerm.taxonomy_id == self.term.taxonomy_id,
                TaxonomyTerm.slug.ancestor_of(self.term.slug),
            )
        ret = self._filter_taxonomy(ret)
        return ret.filter(TaxonomyTerm.slug.ancestor_of(self.slug))

    @property
    def leaf_slug(self):
        if self.slug:
            return self.slug.split('/')[-1]
        if self.term:
            return self.term.slug.split('/')[-1]

    @property
    def whole_slug(self):
        if self.slug:
            return self.slug
        if self.term:
            return self.term.slug

    def get_taxonomy(self, session):
        if isinstance(self.taxonomy, Taxonomy):
            return self.taxonomy
        if self.term:
            return self.term.taxonomy
        if isinstance(self.taxonomy, str):
            return session.query(Taxonomy).filter(Taxonomy.code == self.taxonomy).one()
        else:
            return session.query(Taxonomy).filter(Taxonomy.id == self.taxonomy).one()

    def __eq__(self, other):
        if not isinstance(other, TermIdentification):
            return False
        if self.term:
            if other.term:
                return self.term == other.term
            # other is taxonomy, slug
            if other.slug != self.term.slug:
                return False
            # check if in the same taxonomy
            if isinstance(other.taxonomy, Taxonomy):
                return other.taxonomy.id == self.term.taxonomy_id
            if isinstance(other.taxonomy, str):
                return other.taxonomy == self.term.taxonomy.code
            return other.taxonomy == self.term.taxonomy_id
        if other.term:
            return other == self
        # note: taxonomy
        self_tax = _coerce_tax(self.taxonomy, other.taxonomy)
        other_tax = _coerce_tax(other.taxonomy, self_tax)

        if type(self_tax) != type(other_tax):
            raise ValueError('Can not compare different types of taxonomy identification: %s(%s), %s(%s)' % (
                self_tax, type(self_tax), other_tax, type(other_tax)
            ))

        return self_tax == other_tax and self.slug == other.slug

    @property
    def level(self):
        if self.term:
            return self.term.level
        return len(self.slug.split('/')) - 1

    def contains(self, other):
        if self.whole_slug == other.whole_slug:
            return True
        return other.whole_slug.startswith(self.whole_slug + '/')

    def __str__(self):
        if self.term:
            return str(self.term)
        if self.slug:
            return '%s/%s' % (self.taxonomy, self.slug)
        return self.taxonomy


def _coerce_tax(tax, target):
    if isinstance(target, Taxonomy):
        return tax
    if isinstance(tax, Taxonomy):
        if isinstance(target, str):
            return tax.code
        return tax.id
    return tax


def _coerce_ti(ti):
    if isinstance(ti, TermIdentification):
        return ti
    if isinstance(ti, TaxonomyTerm):
        return TermIdentification(term=ti)
    return TermIdentification(slug=ti)
