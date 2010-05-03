import optfunc

from basic.blog.models import Post
from dateutil.parser import parse
from django.conf import settings
from django.contrib.comments.models import Comment
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.template.defaultfilters import slugify
from gdata import service

"""
Required Dependencies:
 - dateutils
 - gdata
 - django
 - django basic apps (http://github.com/nathanborror/django-basic-apps)
 - optfunc (http://github.com/simonw/optfunc)

"""


def import_entries(blogger_service, blog_id):
    query = service.Query()
    query.feed = '/feeds/' + blog_id + '/posts/default'
    query.max_results = 999
    feed = blogger_service.Get(query.ToUri())

    for entry in feed.entry:
        site = Site.objects.get(id__exact=settings.SITE_ID)
        entry_id = entry.id.text.split('.post-')[-1]
        title = entry.title.text
        slug = slugify(title[0:50])
        body = entry.content.text
        publish = parse(entry.published.text)

        query = service.Query()
        query.feed = '/feeds/' + blog_id + '/' + entry_id + '/comments/default'
        query.max_results = 999
        comment_feed = blogger_service.Get(query.ToUri())
        try:
            post = Post.objects.get(title = title, slug = slug)
        except Post.DoesNotExist:
            post = Post(
                title = title,
                slug = slug,
                body = body,
                publish = publish,
            )
            post.save()
            post.sites.add(site)
            print "Imported post: %s" % (post)

        for comment in comment_feed.entry:
            if comment.author:
                for author in comment.author:
                    user_name = author.name.text
                    user_email = author.email.text
                    if author.uri:
                        user_uri = author.uri.text
            if comment.updated:
                submit_date = parse(comment.updated.text)
            else:
                submit_date = parse(comment.published.text)
            comment = comment.content.text
            content_type = ContentType.objects.get(app_label="blog", model="post")
            try:
                comment = Comment.objects.get(comment = comment, submit_date = submit_date)
            except Comment.DoesNotExist:
                comment = Comment(
                    site = site,
                    content_type = content_type,
                    object_pk = post.id,
                    user_name = user_name,
                    user_email = user_email,
                    user_url = user_uri,
                    comment = comment,
                    submit_date = submit_date,
                )
                comment.save()
                print "Imported comment: %s" % (comment)

        # Hack to get around some bug that was breaking get_next_by_foo() for Post objects
        p = Post.objects.all()
        for post in p:
            post.save()


@optfunc.arghelp('blog_id', 'your Blogger id')
@optfunc.arghelp('email', 'your email address')
@optfunc.arghelp('password', 'your password')
def blogger_importer(blog_id, email, password):
    """Usage: %prog <blog_id> <email> <password>- Import Blogger entries into Django Basic Blog"""

    blogger_service = service.GDataService(email, password)
    blogger_service.service = 'blogger'
    blogger_service.account_type = 'GOOOGLE'
    blogger_service.server = 'www.blogger.com'
    blogger_service.ProgrammaticLogin()
    import_entries(blogger_service, blog_id)


if __name__ == '__main__':
    optfunc.main(blogger_importer)
