from django.contrib import admin
from models import *

# class RulesInline(admin.TabularInline):
#   model = Headline
#   extra = 1

# class UserAdmin(admin.ModelAdmin):
#   inlines = [HeadlineInline]

class RuleAdmin(admin.ModelAdmin):
  pass

admin.site.register(Rule, RuleAdmin)

class ChannelAdmin(admin.ModelAdmin):
  pass

admin.site.register(Channel, ChannelAdmin)