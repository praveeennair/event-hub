from rest_framework import serializers
from .models import Event, Reservation


class EventSerializer(serializers.ModelSerializer):
    reservations_count = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            'id',
            'title',
            'venue',
            'date',
            'total_seats',
            'available_seats',
            'status',
            'created_at',
            'reservations_count',
        ]

    def get_reservations_count(self, obj):
        return obj.reservations.filter(status='confirmed').count()

    def validate(self, data):
        total_seats = data.get('total_seats')
        available_seats = data.get('available_seats')

        if self.instance:
            if total_seats is None:
                total_seats = self.instance.total_seats
            if available_seats is None:
                available_seats = self.instance.available_seats
        else:
            total_seats = total_seats if total_seats is not None else 0
            available_seats = available_seats if available_seats is not None else 0

        if available_seats > total_seats:
            raise serializers.ValidationError('available_seats cannot exceed total_seats.')
        return data


class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = [
            'id',
            'event',
            'attendee_name',
            'attendee_email',
            'seats_reserved',
            'status',
            'created_at',
        ]
        read_only_fields = ['status', 'created_at']

    def validate_seats_reserved(self, value):
        if value < 1:
            raise serializers.ValidationError('Must reserve at least 1 seat.')
        return value

    def validate(self, data):
        event = data.get('event')
        if not event and self.instance:
            event = self.instance.event

        seats_reserved = data.get('seats_reserved')
        if seats_reserved is None and self.instance:
            seats_reserved = self.instance.seats_reserved

        if event:
            if event.status not in ('upcoming', 'ongoing'):
                raise serializers.ValidationError(
                    f'Cannot reserve seats for a {event.status} event.'
                )
            if seats_reserved is not None and seats_reserved > event.available_seats:
                raise serializers.ValidationError(
                    f'Only {event.available_seats} seat(s) available.'
                )
        return data

    def create(self, validated_data):
        event = validated_data['event']
        event.available_seats -= validated_data['seats_reserved']
        event.save()
        return Reservation.objects.create(**validated_data)
