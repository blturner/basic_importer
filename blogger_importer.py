import sys, getopt
import gdata, atom
from datetime import datetime
from dateutil.parser import parse
from gdata import service
from django.conf import settings
from django.template.defaultfilters import slugify
from django.contrib.sites.models import Site
from django.contrib.contenttypes.models import ContentType
from basic.blog.models import Post
from django.contrib.comments.models import Comment

def import_entries(blogger_service, blog_id):
    query = service.Query()
    query.feed = '/feeds/' + blog_id + '/posts/default'
    query.max_results = 999
    feed = blogger_service.Get(query.ToUri())
    
    for entry in feed.entry:
        site = Site.objects.get(id__exact=settings.SITE_ID)
        entry_id = entry.id.text.split('.post-')[-1]
        title = entry.title.text
        slug = slugify(title)
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
                    submit_date = submit_date,)
                comment.save()
                print "Imported comment: %s" % (comment)
        
        # Hack to get around some bug that was breaking get_next_by_foo() for Post objects
        p = Post.objects.all()
        for post in p:
            post.save()

if __name__ == '__main__':
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'ep', ['blog_id=','email=','password='])
    except getopt.GetoptError, err:
        print str(err)
        usage()
        sys.exit(2)
    blog_id = None
    email = None
    password = None
    for o, a in opts:
        if o in ("--blog_id"):
            blog_id = a
        elif o in ("-e", "--email"):
            email = a
        elif o in ("-p", "--password"):
            password = a
        else:
            assert False, "unhandled option"
    blogger_service = service.GDataService(email, password)
    blogger_service.service = 'blogger'
    blogger_service.account_type = 'GOOOGLE'
    blogger_service.server = 'www.blogger.com'
    blogger_service.ProgrammaticLogin()
    import_entries(blogger_service, blog_id)
