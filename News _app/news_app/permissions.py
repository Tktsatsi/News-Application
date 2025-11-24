"""
Custom permission classes for role-based access control.

This module defines permission classes that restrict access based on
user roles (Reader, Editor, Journalist).
"""

from rest_framework import permissions


class IsEditor(permissions.BasePermission):
    """
    Permission class that allows only users with Editor role.

    This permission checks if the user has the 'editor' role.
    """

    def has_permission(self, request, view):
        """
        Check if user has editor role.

        :param request: The HTTP request object
        :type request: HttpRequest
        :param view: The view being accessed
        :type view: View
        :returns: True if user is an editor, False otherwise
        :rtype: bool
        """
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "editor"
        )


class IsJournalist(permissions.BasePermission):
    """
    Permission class that allows only users with Journalist role.

    This permission checks if the user has the 'journalist' role.
    """

    def has_permission(self, request, view):
        """
        Check if user has journalist role.

        :param request: The HTTP request object
        :type request: HttpRequest
        :param view: The view being accessed
        :type view: View
        :returns: True if user is a journalist, False otherwise
        :rtype: bool
        """
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "journalist"
        )


class IsReader(permissions.BasePermission):
    """
    Permission class that allows only users with Reader role.

    This permission checks if the user has the 'reader' role.
    """

    def has_permission(self, request, view):
        """
        Check if user has reader role.

        :param request: The HTTP request object
        :type request: HttpRequest
        :param view: The view being accessed
        :type view: View
        :returns: True if user is a reader, False otherwise
        :rtype: bool
        """
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "reader"
        )


class IsJournalistOrReadOnly(permissions.BasePermission):
    """
    Permission allowing journalists to edit, others to read.

    This permission allows journalists to create/edit content,
    while allowing read-only access to all authenticated users.
    """

    def has_permission(self, request, view):
        """
        Check permissions based on request method.

        :param request: The HTTP request object
        :type request: HttpRequest
        :param view: The view being accessed
        :type view: View
        :returns: True if user has appropriate permissions
        :rtype: bool
        """
        if not request.user or not request.user.is_authenticated:
            return False

        # Read permissions for safe methods
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only for journalists
        return request.user.role == "journalist"


class IsEditorOrReadOnly(permissions.BasePermission):
    """
    Permission allowing editors to edit, others to read.

    This permission allows editors to modify/delete content,
    while allowing read-only access to all authenticated users.
    """

    def has_permission(self, request, view):
        """
        Check permissions based on request method.

        :param request: The HTTP request object
        :type request: HttpRequest
        :param view: The view being accessed
        :type view: View
        :returns: True if user has appropriate permissions
        :rtype: bool
        """
        if not request.user or not request.user.is_authenticated:
            return False

        # Read permissions for safe methods
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write/Delete permissions only for editors
        return request.user.role == "editor"
